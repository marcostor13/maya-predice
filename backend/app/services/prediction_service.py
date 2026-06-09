"""Orquestación de predicciones: modelo entrenado + ajuste por disponibilidad.

Genera la predicción de un partido usando el modelo Dixon-Coles entrenado con el
histórico, ajustando la fuerza de cada equipo según la disponibilidad de su
plantilla (lesiones/sanciones/dudas), y la persiste con su `model_version`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.squad import Player
from app.models.team import Team
from app.services.prediction.availability import (
    AvailabilityConfig,
    PlayerImpact,
    compute_team_adjustment,
)
from app.services.prediction.dixon_coles import DixonColesModel, TeamAdjustment
from app.services.prediction.training import train_model

# Reexport para compatibilidad con callers previos.
__all__ = ["train_model", "predict_and_store"]


async def _team_adjustment(db: AsyncSession, team_id: int | None):
    """Calcula el ajuste por disponibilidad de la plantilla de un equipo."""
    if team_id is None or not settings.enable_availability_adjustment:
        return TeamAdjustment(), None

    players = (
        await db.execute(select(Player).where(Player.team_id == team_id))
    ).scalars().all()
    if not players:
        return TeamAdjustment(), None

    cfg = AvailabilityConfig(adj_strength=settings.availability_adj_strength)
    impacts = [PlayerImpact(p.position, p.role, p.status) for p in players]
    adj, availability = compute_team_adjustment(impacts, cfg)
    info = {
        "attack_availability": availability.attack_availability,
        "defense_availability": availability.defense_availability,
        "attack_delta": round(adj.attack_delta, 4),
        "defense_delta": round(adj.defense_delta, 4),
    }
    return adj, info


async def predict_and_store(
    db: AsyncSession, match: Match, model: DixonColesModel, *, neutral: bool = True
) -> Prediction:
    """Genera y persiste la predicción de un partido (con ajuste por plantilla)."""
    codes = {t.id: t.code for t in (await db.execute(select(Team))).scalars().all()}
    home, away = codes.get(match.home_team_id), codes.get(match.away_team_id)
    if home is None or away is None:
        raise KeyError("El partido no tiene ambas selecciones definidas todavía.")

    home_adj, home_info = await _team_adjustment(db, match.home_team_id)
    away_adj, away_info = await _team_adjustment(db, match.away_team_id)

    probs = model.predict(home, away, neutral=neutral, home_adj=home_adj, away_adj=away_adj)

    prediction = Prediction(
        match_id=match.id,
        model_version=settings.model_version,
        p_home=probs.p_home,
        p_draw=probs.p_draw,
        p_away=probs.p_away,
        expected_home_goals=probs.expected_home_goals,
        expected_away_goals=probs.expected_away_goals,
        scoreline_probs=probs.top_scorelines(5),
        adjustments={"home": home_info, "away": away_info, "neutral": neutral},
    )
    db.add(prediction)
    await db.flush()
    return prediction
