"""Motor de consenso multi-fuente (puro, sin DB ni red).

Dado el mismo jugador/entrenador observado por varias fuentes, decide el valor
de cada campo por **voto mayoritario** (desempate por prioridad de fuente),
calcula el **grado de acuerdo** (`agreement`) y registra los **conflictos**
(qué dijo cada fuente). Esto es lo que aporta veracidad: cuantas más fuentes
coinciden, mayor es la confianza.

Probar este módulo no requiere infraestructura: es determinista y puro.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.data.players.base import (
    CoachObservation,
    PlayerObservation,
    normalize_name,
)
from app.models.squad import PlayerStatus, Position, SquadRole

# Prioridad por defecto para desempatar (la primera gana ante empate de votos).
DEFAULT_PRIORITY = ("apifootball", "thesportsdb", "wikidata", "fixture")


@dataclass
class ConsensusValue:
    field: str
    value: Any
    agreement: float          # acuerdo entre las fuentes que reportaron el campo (0..1)
    reported_by: int          # cuántas fuentes reportaron algún valor
    by_source: dict[str, str] # fuente -> valor reportado (trazabilidad)
    has_conflict: bool


def _priority_index(source: str, priority: tuple[str, ...]) -> int:
    return priority.index(source) if source in priority else len(priority)


def merge_field(
    field: str,
    pairs: list[tuple[str, Any]],
    priority: tuple[str, ...] = DEFAULT_PRIORITY,
) -> ConsensusValue:
    """Combina los valores de un campo provenientes de varias fuentes.

    `pairs`: lista de (fuente, valor). Los valores None se ignoran para el voto
    pero la fuente queda registrada en `by_source` solo si aportó valor.
    """
    reported = [(s, v) for s, v in pairs if v is not None and v != ""]
    by_source = {s: _stringify(v) for s, v in reported}

    if not reported:
        return ConsensusValue(field, None, 0.0, 0, {}, False)

    counts = Counter(_stringify(v) for _, v in reported)
    top = max(counts.values())
    # candidatos empatados en votos -> desempatar por prioridad de fuente
    tied = {key for key, c in counts.items() if c == top}
    chosen_key = min(
        ((s, _stringify(v)) for s, v in reported if _stringify(v) in tied),
        key=lambda sv: _priority_index(sv[0], priority),
    )[1]
    chosen_value = next(v for _, v in reported if _stringify(v) == chosen_key)

    agreement = top / len(reported)
    has_conflict = len(counts) > 1
    return ConsensusValue(field, chosen_value, agreement, len(reported), by_source, has_conflict)


def _stringify(value: Any) -> str:
    if isinstance(value, (Position, PlayerStatus, SquadRole)):
        return value.value
    return str(value)


@dataclass
class PlayerConsensus:
    name_key: str
    full_name: str
    fields: dict[str, ConsensusValue]
    sources_count: int
    confidence: float  # media de los acuerdos por campo reportado (0..1)

    def value(self, field: str) -> Any:
        cv = self.fields.get(field)
        return cv.value if cv else None

    @property
    def conflicts(self) -> list[ConsensusValue]:
        return [cv for cv in self.fields.values() if cv.has_conflict]


@dataclass
class CoachConsensus:
    name: str
    fields: dict[str, ConsensusValue]
    sources_count: int
    confidence: float

    def value(self, field: str) -> Any:
        cv = self.fields.get(field)
        return cv.value if cv else None

    @property
    def conflicts(self) -> list[ConsensusValue]:
        return [cv for cv in self.fields.values() if cv.has_conflict]


_PLAYER_FIELDS = ("full_name", "position", "shirt_number", "club", "birth_date", "role", "status")


def build_player_consensus(
    observations: list[PlayerObservation],
    priority: tuple[str, ...] = DEFAULT_PRIORITY,
) -> PlayerConsensus:
    """Construye el dato consensuado de un jugador a partir de N observaciones."""
    if not observations:
        raise ValueError("Se requiere al menos una observación.")

    sources = {o.source for o in observations}
    fields: dict[str, ConsensusValue] = {}
    for f in _PLAYER_FIELDS:
        pairs = [(o.source, getattr(o, f)) for o in observations]
        fields[f] = merge_field(f, pairs, priority)

    reported = [cv for cv in fields.values() if cv.reported_by > 0]
    confidence = sum(cv.agreement for cv in reported) / len(reported) if reported else 0.0

    full_name = fields["full_name"].value or observations[0].full_name
    return PlayerConsensus(
        name_key=normalize_name(full_name),
        full_name=full_name,
        fields=fields,
        sources_count=len(sources),
        confidence=round(confidence, 3),
    )


_COACH_FIELDS = ("name", "nationality", "status")


def build_coach_consensus(
    observations: list[CoachObservation],
    priority: tuple[str, ...] = DEFAULT_PRIORITY,
) -> CoachConsensus:
    if not observations:
        raise ValueError("Se requiere al menos una observación.")
    sources = {o.source for o in observations}
    fields = {
        f: merge_field(f, [(o.source, getattr(o, f)) for o in observations], priority)
        for f in _COACH_FIELDS
    }
    reported = [cv for cv in fields.values() if cv.reported_by > 0]
    confidence = sum(cv.agreement for cv in reported) / len(reported) if reported else 0.0
    return CoachConsensus(
        name=fields["name"].value or observations[0].name,
        fields=fields,
        sources_count=len(sources),
        confidence=round(confidence, 3),
    )
