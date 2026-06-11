"""Contrato común de los proveedores de marcadores en vivo (in-play)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LiveFixture:
    """Un partido en juego observado por una fuente live.

    Los códigos pueden ser None si la fuente no se pudo mapear a una de las 48
    selecciones; en ese caso se conserva el nombre para diagnóstico.
    """

    home_code: str | None
    away_code: str | None
    home_name: str | None
    away_name: str | None
    kickoff_date: date | None
    minute: int | None
    status: str
    home_goals: int | None
    away_goals: int | None
    finished: bool


class LiveProvider(ABC):
    """Interfaz de un proveedor de marcadores en vivo."""

    name: str = "base"

    @abstractmethod
    async def fetch_live(self) -> list[LiveFixture]:
        """Devuelve los partidos actualmente en juego (in-play)."""
        raise NotImplementedError
