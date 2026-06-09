"""Proveedores de datos de plantillas (jugadores, suplentes y entrenadores).

Multi-fuente: cada proveedor implementa `PlayerDataProvider` y entrega
`SquadObservation` normalizadas. El servicio de plantillas reúne las
observaciones de varias fuentes y construye el dato final por consenso
(ver `services/squad/consensus.py`).
"""

from app.data.players.base import (
    CoachObservation,
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
    normalize_name,
    normalize_position,
    normalize_status,
)

__all__ = [
    "CoachObservation",
    "PlayerDataProvider",
    "PlayerObservation",
    "SquadObservation",
    "normalize_name",
    "normalize_position",
    "normalize_status",
]
