"""Modelo de predicción: salida del modelo para un partido (versionada)."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    model_version: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    p_home: Mapped[float] = mapped_column(Float, nullable=False)
    p_draw: Mapped[float] = mapped_column(Float, nullable=False)
    p_away: Mapped[float] = mapped_column(Float, nullable=False)

    expected_home_goals: Mapped[float] = mapped_column(Float, nullable=False)
    expected_away_goals: Mapped[float] = mapped_column(Float, nullable=False)

    # Top marcadores y/o matriz de probabilidad serializada como JSON.
    # p.ej. [{"home": 2, "away": 1, "prob": 0.11}, ...]
    scoreline_probs: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Ajustes aplicados por disponibilidad de jugadores (transparencia/auditoría).
    # p.ej. {"home": {"attack_availability": 0.92, ...}, "away": {...}, "neutral": true}
    adjustments: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Ensamble con el mercado: si se mezcló con cuotas, guarda la terna del modelo,
    # la del mercado y el peso ω usado. Null = predicción solo-modelo.
    # p.ej. {"model": [.5,.3,.2], "market": [.45,.3,.25], "weight": 0.4}
    ensemble: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match = relationship("Match", back_populates="predictions")
