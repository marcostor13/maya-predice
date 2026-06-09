"""Consenso multi-fuente para datos de plantillas."""

from app.services.squad.consensus import (
    CoachConsensus,
    ConsensusValue,
    PlayerConsensus,
    build_coach_consensus,
    build_player_consensus,
    merge_field,
)

__all__ = [
    "ConsensusValue",
    "CoachConsensus",
    "PlayerConsensus",
    "build_coach_consensus",
    "build_player_consensus",
    "merge_field",
]
