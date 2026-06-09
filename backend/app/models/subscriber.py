"""Suscriptores que reciben novedades y predicciones por correo."""

import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _token() -> str:
    return secrets.token_urlsafe(24)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    # Token único para el enlace de baja (unsubscribe) de cada suscriptor.
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=_token)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
