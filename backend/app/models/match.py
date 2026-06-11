"""Modelo de partido."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MatchStage(str, enum.Enum):
    GROUP = "group"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER = "quarter_final"
    SEMI = "semi_final"
    THIRD_PLACE = "third_place"
    FINAL = "final"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    # Clave estable de la fuente oficial; permite upsert idempotente.
    external_ref: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)

    # Nullable: en eliminatorias los participantes pueden no estar definidos aún.
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    # Placeholder de la fuente cuando el equipo no está definido (p.ej. "1A", "W101").
    home_placeholder: Mapped[str | None] = mapped_column(String(16), nullable=True)
    away_placeholder: Mapped[str | None] = mapped_column(String(16), nullable=True)

    stage: Mapped[MatchStage] = mapped_column(Enum(MatchStage), default=MatchStage.GROUP)
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group: Mapped[str | None] = mapped_column(String(2), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(120), nullable=True)
    kickoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), default=MatchStatus.SCHEDULED)
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Marcador en vivo (in-play): minuto de juego y momento de la última actualización.
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    live_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament = relationship("Tournament", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    predictions = relationship(
        "Prediction", back_populates="match", cascade="all, delete-orphan"
    )
