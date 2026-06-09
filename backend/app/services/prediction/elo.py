"""Ratings Elo internacionales calculados desde el histórico de resultados.

El Elo incorpora la dificultad del rival, la diferencia de goles y la localía, y
es un excelente **prior de fuerza** para el modelo Dixon-Coles (regulariza a los
equipos con pocos partidos recientes). Se calcula a partir de los mismos
resultados que entrenan el modelo, así que es reproducible y no añade una fuente
externa.

Variante estilo *World Football Elo*: factor K con multiplicador por diferencia
de goles y ventaja de localía en sedes no neutrales.

Módulo puro y determinista: testeable sin DB ni red.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.services.prediction.dixon_coles import MatchResult

_SENTINEL_DATE = date(9999, 12, 31)


@dataclass
class EloConfig:
    base: float = 1500.0
    k: float = 40.0
    home_advantage: float = 65.0  # puntos Elo de localía (no se aplica en neutral)


def _gd_multiplier(goal_diff: int) -> float:
    if goal_diff <= 1:
        return 1.0
    if goal_diff == 2:
        return 1.5
    if goal_diff == 3:
        return 1.75
    return 1.75 + (goal_diff - 3) / 8.0


def compute_elo(
    matches: list[MatchResult], config: EloConfig | None = None
) -> dict[str, float]:
    """Calcula el Elo final de cada equipo procesando los partidos en orden."""
    cfg = config or EloConfig()
    ratings: dict[str, float] = defaultdict(lambda: cfg.base)

    for m in sorted(matches, key=lambda x: x.played_on or _SENTINEL_DATE):
        ra, rb = ratings[m.home], ratings[m.away]
        ha = 0.0 if m.neutral else cfg.home_advantage
        expected_home = 1.0 / (1.0 + 10 ** ((rb - (ra + ha)) / 400.0))

        if m.home_goals > m.away_goals:
            score_home = 1.0
        elif m.home_goals < m.away_goals:
            score_home = 0.0
        else:
            score_home = 0.5

        k = cfg.k * _gd_multiplier(abs(m.home_goals - m.away_goals))
        delta = k * (score_home - expected_home)
        ratings[m.home] = ra + delta
        ratings[m.away] = rb - delta

    return dict(ratings)


def elo_to_priors(elo: dict[str, float], scale: float = 0.5) -> dict[str, float]:
    """Convierte Elo en un prior de fuerza neta (z-score escalado) por equipo.

    El resultado es el valor objetivo de `attack - defense` hacia el que el modelo
    se regulariza. Media 0; `scale` controla la dispersión esperada en log-goles.
    """
    if not elo:
        return {}
    values = list(elo.values())
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    std = var**0.5 or 1.0
    return {team: ((r - mean) / std) * scale for team, r in elo.items()}
