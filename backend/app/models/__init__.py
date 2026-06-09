"""Modelos ORM. Importados aquí para que Alembic los detecte."""

from app.models.match import Match, MatchStage, MatchStatus
from app.models.prediction import Prediction
from app.models.team import Team, TeamStrength
from app.models.tournament import Tournament

__all__ = [
    "Match",
    "MatchStage",
    "MatchStatus",
    "Prediction",
    "Team",
    "TeamStrength",
    "Tournament",
]
