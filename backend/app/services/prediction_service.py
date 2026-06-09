"""Servicio que orquesta el modelo de predicción con la base de datos.

Carga partidos históricos finalizados, entrena el modelo Dixon-Coles, genera
predicciones para partidos programados y las persiste con su `model_version`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.team import Team
from app.services.prediction.dixon_coles import DixonColesModel, MatchResult


async def _load_team_codes(db: AsyncSession) -> dict[int, str]:
    rows = (await db.execute(select(Team.id, Team.code))).all()
    return {row.id: row.code for row in rows}


async def train_model(db: AsyncSession, xi: float = 0.0) -> DixonColesModel:
    """Entrena el modelo con los partidos finalizados disponibles."""
    codes = await _load_team_codes(db)
    result = await db.execute(select(Match).where(Match.status == MatchStatus.FINISHED))
    matches = result.scalars().all()

    history = [
        MatchResult(
            home=codes[m.home_team_id],
            away=codes[m.away_team_id],
            home_goals=m.home_goals or 0,
            away_goals=m.away_goals or 0,
            played_on=m.kickoff.date() if m.kickoff else None,
        )
        for m in matches
        if m.home_team_id in codes and m.away_team_id in codes
    ]
    model = DixonColesModel(xi=xi)
    model.fit(history)
    return model


async def predict_and_store(db: AsyncSession, match: Match, model: DixonColesModel) -> Prediction:
    """Genera la predicción de un partido y la persiste."""
    codes = await _load_team_codes(db)
    home, away = codes[match.home_team_id], codes[match.away_team_id]
    probs = model.predict(home, away)

    prediction = Prediction(
        match_id=match.id,
        model_version=settings.model_version,
        p_home=probs.p_home,
        p_draw=probs.p_draw,
        p_away=probs.p_away,
        expected_home_goals=probs.expected_home_goals,
        expected_away_goals=probs.expected_away_goals,
        scoreline_probs=probs.top_scorelines(5),
    )
    db.add(prediction)
    await db.flush()
    return prediction
