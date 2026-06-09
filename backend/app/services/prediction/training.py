"""Entrenamiento del modelo de predicción a partir del histórico + resultados.

Combina:
- el histórico internacional (martj42) como base de datos de entrenamiento, y
- los resultados ya jugados del torneo (tabla `matches`), que pesan como datos
  recientes y específicos.

Cachea el modelo entrenado en memoria (es costoso reajustarlo en cada request) y
permite persistir las fuerzas por equipo en `team_strengths`.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.history import ResultsHistoryProvider
from app.models.match import Match, MatchStatus
from app.models.team import Team, TeamStrength
from app.services.prediction.dixon_coles import DixonColesModel, MatchResult
from app.services.prediction.elo import compute_elo, elo_to_priors

logger = logging.getLogger("maya.training")

# Caché de modelo en proceso, por versión.
_CACHE: dict[str, DixonColesModel] = {}


async def _tournament_results(db: AsyncSession) -> list[MatchResult]:
    """Resultados ya jugados del torneo, como datos de entrenamiento (no neutrales
    salvo que se indique; en un Mundial casi todo es sede neutral)."""
    id_to_code = {
        t.id: t.code for t in (await db.execute(select(Team.id, Team.code))).all()
    }
    rows = (
        await db.execute(select(Match).where(Match.status == MatchStatus.FINISHED))
    ).scalars().all()
    results: list[MatchResult] = []
    for m in rows:
        h, a = id_to_code.get(m.home_team_id), id_to_code.get(m.away_team_id)
        if h and a and m.home_goals is not None and m.away_goals is not None:
            results.append(
                MatchResult(h, a, m.home_goals, m.away_goals, played_on=None, neutral=True)
            )
    return results


async def train_model(db: AsyncSession, *, force: bool = False) -> DixonColesModel:
    """Entrena (o devuelve de caché) el modelo Dixon-Coles."""
    version = settings.model_version
    if not force and version in _CACHE:
        return _CACHE[version]

    history = await ResultsHistoryProvider().fetch_results()
    tournament = await _tournament_results(db)
    dataset = history + tournament
    if not dataset:
        raise ValueError("No hay datos de entrenamiento (histórico vacío).")

    # Elo como prior de fuerza (regulariza a equipos con pocos partidos).
    elo = compute_elo(dataset)
    priors = elo_to_priors(elo) if settings.elo_prior_weight > 0 else None

    model = DixonColesModel(xi=settings.model_decay_xi)
    model.fit(dataset, priors=priors, prior_weight=settings.elo_prior_weight)
    model.elo = elo  # type: ignore[attr-defined]
    _CACHE[version] = model
    logger.info(
        "Modelo entrenado: %s equipos, %s partidos (%s histórico + %s torneo), prior Elo=%s.",
        len(model.teams),
        len(dataset),
        len(history),
        len(tournament),
        settings.elo_prior_weight,
    )
    return model


def clear_cache() -> None:
    _CACHE.clear()


async def persist_team_strengths(db: AsyncSession, model: DixonColesModel) -> int:
    """Guarda ataque/defensa por equipo en `team_strengths` (para mostrar/auditar)."""
    teams = {t.code: t for t in (await db.execute(select(Team))).scalars().all()}
    elo = getattr(model, "elo", {}) or {}
    count = 0
    for code, team in teams.items():
        if code in model.attack:
            db.add(
                TeamStrength(
                    team_id=team.id,
                    model_version=settings.model_version,
                    attack=model.attack[code],
                    defense=model.defense[code],
                    elo=elo.get(code),
                )
            )
            count += 1
    return count
