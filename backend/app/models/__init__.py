"""Modelos ORM. Importados aquí para que Alembic los detecte."""

from app.models.match import Match, MatchStage, MatchStatus
from app.models.prediction import Prediction
from app.models.sync import DataChange, SyncRun, SyncStatus
from app.models.team import Team, TeamStrength
from app.models.tournament import Tournament

__all__ = [
    "DataChange",
    "Match",
    "MatchStage",
    "MatchStatus",
    "Prediction",
    "SyncRun",
    "SyncStatus",
    "Team",
    "TeamStrength",
    "Tournament",
]
