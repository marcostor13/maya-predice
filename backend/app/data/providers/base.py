"""Contrato común de los proveedores de datos oficiales."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.match import MatchStage


@dataclass(frozen=True)
class ProviderMatch:
    """Partido normalizado tal como lo entrega un proveedor de datos.

    Las selecciones pueden no estar definidas todavía (fases eliminatorias): en
    ese caso `home_code`/`away_code` son None y se conserva el placeholder de la
    fuente (p.ej. "1A", "W101") en `home_placeholder`/`away_placeholder`.
    """

    external_ref: str  # clave estable para upsert (no cambia entre sincronizaciones)
    stage: MatchStage
    matchday: int | None
    group: str | None

    home_name: str | None
    away_name: str | None
    home_code: str | None
    away_code: str | None
    home_confederation: str | None
    away_confederation: str | None
    home_placeholder: str | None
    away_placeholder: str | None

    kickoff: datetime | None  # en UTC
    venue: str | None

    home_goals: int | None
    away_goals: int | None

    @property
    def is_finished(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None


class DataProvider(ABC):
    """Interfaz de un proveedor de datos del torneo."""

    name: str = "base"

    @abstractmethod
    async def fetch_matches(self) -> list[ProviderMatch]:
        """Obtiene y normaliza todos los partidos del torneo."""
        raise NotImplementedError
