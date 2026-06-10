"""Overrides de configuración en runtime (editables desde el panel admin).

Cada fila pisa el valor por defecto/entorno de un ajuste **operativo** (no los
hiperparámetros del modelo, que están blindados). Se aplican sobre el `settings`
en memoria al arrancar y al inicio de cada job (para que los 2 workers Gunicorn
converjan). Ver `app/services/app_settings.py`.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
