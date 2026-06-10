"""Registro de trabajos en segundo plano del panel admin (jobs largos).

Permite que una operación pesada (el recompute) se ejecute **sin bloquear** la
petición HTTP: el endpoint crea un `JobRun` en estado `running`, dispara la tarea
y responde al instante; el panel consulta el estado por polling. Como en
producción hay **varios workers Gunicorn**, el estado vive en la DB (no en
memoria del proceso) para que cualquier worker lo pueda leer.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), index=True)  # p.ej. "recompute"
    # running | done | error
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # resumen del pipeline
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(20), default="admin")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
