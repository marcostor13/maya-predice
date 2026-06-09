"""Modelos ORM. Importados aquí para que Alembic los detecte."""

from app.models.match import Match, MatchStage, MatchStatus
from app.models.prediction import Prediction
from app.models.simulation import SimulationResult, SimulationRun
from app.models.squad import (
    Coach,
    Player,
    PlayerStatus,
    Position,
    SquadDiscrepancy,
    SquadRole,
)
from app.models.subscriber import Subscriber
from app.models.sync import DataChange, SyncRun, SyncStatus
from app.models.team import Team, TeamStrength
from app.models.tournament import Tournament

__all__ = [
    "Coach",
    "DataChange",
    "Match",
    "MatchStage",
    "MatchStatus",
    "Player",
    "PlayerStatus",
    "Position",
    "Prediction",
    "SimulationResult",
    "SimulationRun",
    "SquadDiscrepancy",
    "SquadRole",
    "Subscriber",
    "SyncRun",
    "SyncStatus",
    "Team",
    "TeamStrength",
    "Tournament",
]
