"""Modelos de selección y de su fuerza estimada por el modelo."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)  # ISO-3, p.ej. ARG
    confederation: Mapped[str | None] = mapped_column(String(20), nullable=True)  # UEFA, CONMEBOL...
    group: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)  # A..L
    fifa_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    strengths = relationship(
        "TeamStrength", back_populates="team", cascade="all, delete-orphan"
    )


class TeamStrength(Base):
    """Parámetros ataque/defensa estimados por una versión del modelo."""

    __tablename__ = "team_strengths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    attack: Mapped[float] = mapped_column(Float, nullable=False)
    defense: Mapped[float] = mapped_column(Float, nullable=False)
    elo: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="strengths")
