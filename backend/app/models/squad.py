"""Modelos de plantillas: jugadores, entrenadores y discrepancias entre fuentes.

El estado de cada jugador/entrenador se construye por **consenso de varias
fuentes** (ver `services/squad/consensus.py`). Se guarda:
- el valor consensuado por campo,
- `confidence` (grado de acuerdo entre fuentes) y `sources_count`,
- `source_data` (qué reportó cada fuente, para trazabilidad/veracidad),
- y, cuando las fuentes no coinciden, una fila en `squad_discrepancies`.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Position(str, enum.Enum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"
    UNKNOWN = "UNKNOWN"


class PlayerStatus(str, enum.Enum):
    AVAILABLE = "available"
    INJURED = "injured"
    SUSPENDED = "suspended"
    DOUBTFUL = "doubtful"
    OUT = "out"
    UNKNOWN = "unknown"


class SquadRole(str, enum.Enum):
    STARTER = "starter"
    SUBSTITUTE = "substitute"
    RESERVE = "reserve"
    UNKNOWN = "unknown"


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    nationality: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[PlayerStatus] = mapped_column(Enum(PlayerStatus), default=PlayerStatus.AVAILABLE)

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sources_count: Mapped[int] = mapped_column(Integer, default=0)
    source_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team = relationship("Team")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Nombre normalizado (sin acentos, minúsculas) usado como clave de identidad
    # entre fuentes. Único por equipo.
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    # 'position' es palabra reservada en SQL -> se mapea a la columna 'player_position'
    # (el atributo Python y la API siguen usando 'position').
    position: Mapped[Position] = mapped_column(
        "player_position", Enum(Position, name="position_enum"), default=Position.UNKNOWN
    )
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    club: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    role: Mapped[SquadRole] = mapped_column(Enum(SquadRole), default=SquadRole.UNKNOWN)
    status: Mapped[PlayerStatus] = mapped_column(Enum(PlayerStatus), default=PlayerStatus.UNKNOWN)

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sources_count: Mapped[int] = mapped_column(Integer, default=0)
    source_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team = relationship("Team")


class SquadDiscrepancy(Base):
    """Conflicto entre fuentes para un campo concreto de un jugador/entrenador."""

    __tablename__ = "squad_discrepancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("sync_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    team_code: Mapped[str] = mapped_column(String(3), index=True)
    entity_type: Mapped[str] = mapped_column(String(10))  # player | coach
    entity_name: Mapped[str] = mapped_column(String(120))
    field: Mapped[str] = mapped_column(String(40))
    chosen_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agreement: Mapped[float] = mapped_column(Float, default=0.0)
    by_source: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {fuente: valor}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
