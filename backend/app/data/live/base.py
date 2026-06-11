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


@dataclass(frozen=True)
class LiveCandidate:
    """Un partido candidato (probablemente in-play) que el servicio ya resolvió.

    Lo usan las fuentes que no pueden listar "todos los live" por sí solas
    (p. ej. Google), que necesitan saber qué partidos consultar.
    """

    home_code: str | None
    away_code: str | None
    home_name: str | None
    away_name: str | None
    kickoff_date: date | None


class LiveProvider(ABC):
    """Interfaz de un proveedor de marcadores en vivo."""

    name: str = "base"

    @abstractmethod
    async def fetch_live(
        self, candidates: list[LiveCandidate] | None = None
    ) -> list[LiveFixture]:
        """Devuelve los partidos actualmente en juego (in-play).

        `candidates` es una pista opcional con los partidos que el servicio cree
        en juego; las fuentes que listan todo lo ignoran, las que no (Google) lo
        usan para saber qué consultar.
        """
        raise NotImplementedError
