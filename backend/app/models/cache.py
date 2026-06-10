"""Caché persistente de respuestas de APIs externas.

Guarda la respuesta JSON de cada consulta (keyed por endpoint+parámetros, sin el
token) para **no volver a pedir la misma información** y ahorrar créditos de la API
(p.ej. Sportmonks). Ver `app/data/players/_cache.py`.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApiCache(Base):
    __tablename__ = "api_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # hash sha256 del endpoint + parámetros (sin token) -> identifica la consulta
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default="")  # p.ej. "sportmonks"
    request: Mapped[str | None] = mapped_column(Text, nullable=True)  # legible (debug)
    response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
