"""Contrato y normalización común de los proveedores de plantillas."""

from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from app.models.squad import PlayerStatus, Position, SquadRole

# --- Normalización (compartida por todos los proveedores) ---

_POSITION_MAP = {
    "gk": Position.GK, "goalkeeper": Position.GK, "g": Position.GK, "portero": Position.GK,
    "def": Position.DEF, "defender": Position.DEF, "defence": Position.DEF, "d": Position.DEF,
    "back": Position.DEF, "defensa": Position.DEF, "centre-back": Position.DEF,
    "mid": Position.MID, "midfielder": Position.MID, "m": Position.MID, "medio": Position.MID,
    "centrocampista": Position.MID,
    "fwd": Position.FWD, "forward": Position.FWD, "attacker": Position.FWD, "f": Position.FWD,
    "striker": Position.FWD, "winger": Position.FWD, "delantero": Position.FWD,
}

_STATUS_MAP = {
    "injured": PlayerStatus.INJURED, "injury": PlayerStatus.INJURED, "lesionado": PlayerStatus.INJURED,
    "suspended": PlayerStatus.SUSPENDED, "suspension": PlayerStatus.SUSPENDED,
    "sancionado": PlayerStatus.SUSPENDED,
    "doubtful": PlayerStatus.DOUBTFUL, "questionable": PlayerStatus.DOUBTFUL, "duda": PlayerStatus.DOUBTFUL,
    "out": PlayerStatus.OUT, "unavailable": PlayerStatus.OUT, "baja": PlayerStatus.OUT,
    "available": PlayerStatus.AVAILABLE, "fit": PlayerStatus.AVAILABLE, "active": PlayerStatus.AVAILABLE,
    "disponible": PlayerStatus.AVAILABLE,
}

_ROLE_MAP = {
    "starter": SquadRole.STARTER, "titular": SquadRole.STARTER, "lineup": SquadRole.STARTER,
    "substitute": SquadRole.SUBSTITUTE, "sub": SquadRole.SUBSTITUTE, "suplente": SquadRole.SUBSTITUTE,
    "bench": SquadRole.SUBSTITUTE,
    "reserve": SquadRole.RESERVE, "reserva": SquadRole.RESERVE,
}


def normalize_name(name: str) -> str:
    """Clave de identidad: sin acentos, minúsculas, sin puntuación, espacios simples."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-zA-Z0-9 ]", " ", ascii_only).lower()
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_position(value: str | None) -> Position:
    if not value:
        return Position.UNKNOWN
    return _POSITION_MAP.get(value.strip().lower(), Position.UNKNOWN)


def normalize_status(value: str | None) -> PlayerStatus:
    if not value:
        return PlayerStatus.UNKNOWN
    return _STATUS_MAP.get(value.strip().lower(), PlayerStatus.AVAILABLE)


def normalize_role(value: str | None) -> SquadRole:
    if not value:
        return SquadRole.UNKNOWN
    return _ROLE_MAP.get(value.strip().lower(), SquadRole.UNKNOWN)


# --- Observaciones normalizadas ---

@dataclass(frozen=True)
class PlayerObservation:
    source: str
    full_name: str
    position: Position = Position.UNKNOWN
    shirt_number: int | None = None
    club: str | None = None
    birth_date: date | None = None
    role: SquadRole = SquadRole.UNKNOWN
    status: PlayerStatus = PlayerStatus.UNKNOWN

    @property
    def name_key(self) -> str:
        return normalize_name(self.full_name)


@dataclass(frozen=True)
class CoachObservation:
    source: str
    name: str
    nationality: str | None = None
    status: PlayerStatus = PlayerStatus.AVAILABLE


@dataclass
class SquadObservation:
    source: str
    team_code: str
    coach: CoachObservation | None = None
    players: list[PlayerObservation] = field(default_factory=list)


class PlayerDataProvider(ABC):
    """Interfaz de un proveedor de datos de plantillas."""

    name: str = "base"

    @abstractmethod
    async def fetch_all(self) -> list[SquadObservation]:
        """Devuelve las plantillas observadas por esta fuente (una por equipo)."""
        raise NotImplementedError
