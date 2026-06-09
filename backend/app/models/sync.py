"""Modelos de auditoría de la sincronización con la fuente oficial.

`SyncRun`: una ejecución del job de verificación (diaria o manual).
`DataChange`: cada cambio detectado respecto al estado almacenado (resultado,
horario, sede, resolución de un cruce, etc.). Permite responder "¿qué cambió
hoy?" y auditar el origen de cada dato.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SyncStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), default=SyncStatus.RUNNING)
    trigger: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled | manual

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    matches_seen: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    changes_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    changes = relationship("DataChange", back_populates="run", cascade="all, delete-orphan")


class DataChange(Base):
    __tablename__ = "data_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(
        ForeignKey("sync_runs.id", ondelete="CASCADE"), index=True
    )
    match_id: Mapped[int | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20))  # created | updated
    field: Mapped[str] = mapped_column(String(40))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run = relationship("SyncRun", back_populates="changes")
