"""Modelos del agente de crecimiento (growth).

`GrowthRun` = una ejecución del agente (cron cada `growth_agent_minutes` o manual):
guarda su estado, el modelo usado y un resumen. `GrowthInsight` = cada idea
generada (promoción/SEO/contenido/monetización/técnica) con su prioridad, estado y
acción asociada. Las ideas de monetización quedan `requires_approval=True` y NUNCA
se ejecutan solas. Persistir el historial permite auditar y que el agente construya
sobre ideas previas sin repetirlas.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GrowthRun(Base):
    __tablename__ = "growth_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # running | done | error
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    trigger: Mapped[str] = mapped_column(String(20), default="growth")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    insights = relationship("GrowthInsight", back_populates="run", cascade="all, delete-orphan")


class GrowthInsight(Base):
    __tablename__ = "growth_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("growth_runs.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # seo | promotion | content | monetization | technical
    category: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1 (alta) .. 5 (baja)
    # new | emailed | approved | done | dismissed
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    # email_only | social_post | seo_suggestion | auto_sitemap | indexnow | ...
    action_type: Mapped[str] = mapped_column(String(30), default="email_only")
    # Contenido listo para usar (texto de un post, keywords, etc.).
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run = relationship("GrowthRun", back_populates="insights")
