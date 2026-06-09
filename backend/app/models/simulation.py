"""Resultados de la simulación Monte Carlo del torneo.

`SimulationRun` = una ejecución (versión de modelo, nº de iteraciones, fecha).
`SimulationResult` = probabilidades por selección de alcanzar cada fase y de ser
campeona. Se recalcula al actualizarse los resultados (ver recompute).
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    trigger: Mapped[str] = mapped_column(String(20), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    results = relationship(
        "SimulationResult", back_populates="run", cascade="all, delete-orphan"
    )


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)

    advance_prob: Mapped[float] = mapped_column(Float, default=0.0)  # supera la fase de grupos
    round16_prob: Mapped[float] = mapped_column(Float, default=0.0)
    quarter_prob: Mapped[float] = mapped_column(Float, default=0.0)
    semi_prob: Mapped[float] = mapped_column(Float, default=0.0)
    final_prob: Mapped[float] = mapped_column(Float, default=0.0)
    champion_prob: Mapped[float] = mapped_column(Float, default=0.0)

    run = relationship("SimulationRun", back_populates="results")
    team = relationship("Team")
