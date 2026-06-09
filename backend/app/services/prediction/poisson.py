"""Utilidades de la distribución de Poisson aplicadas a marcadores de fútbol.

A partir de los goles esperados del local (lambda) y del visitante (mu) se
construye la matriz de probabilidad de cada marcador posible y, agregando, las
probabilidades 1X2 (victoria local / empate / victoria visitante).

Incluye la corrección tau de Dixon-Coles para marcadores bajos, que ajusta la
dependencia entre goles de ambos equipos que el Poisson independiente no captura.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import poisson

MAX_GOALS = 10  # marcadores 0..10 por equipo


@dataclass
class MatchProbabilities:
    """Resultado de una predicción de partido."""

    p_home: float
    p_draw: float
    p_away: float
    expected_home_goals: float
    expected_away_goals: float
    score_matrix: np.ndarray  # [home_goals, away_goals]

    def top_scorelines(self, n: int = 5) -> list[dict]:
        """Devuelve los n marcadores más probables."""
        flat = [
            {"home": h, "away": a, "prob": float(self.score_matrix[h, a])}
            for h in range(self.score_matrix.shape[0])
            for a in range(self.score_matrix.shape[1])
        ]
        flat.sort(key=lambda x: x["prob"], reverse=True)
        return flat[:n]


def _tau(home: int, away: int, lam: float, mu: float, rho: float) -> float:
    """Factor de corrección de Dixon-Coles para marcadores de pocos goles."""
    if home == 0 and away == 0:
        return 1.0 - lam * mu * rho
    if home == 0 and away == 1:
        return 1.0 + lam * rho
    if home == 1 and away == 0:
        return 1.0 + mu * rho
    if home == 1 and away == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(
    lam: float, mu: float, rho: float = 0.0, max_goals: int = MAX_GOALS
) -> np.ndarray:
    """Matriz (max_goals+1 x max_goals+1) de P(home=i, away=j).

    `rho` es el parámetro de dependencia de Dixon-Coles (rho=0 => Poisson puro).
    """
    home_pmf = poisson.pmf(np.arange(max_goals + 1), lam)
    away_pmf = poisson.pmf(np.arange(max_goals + 1), mu)
    matrix = np.outer(home_pmf, away_pmf)

    if rho != 0.0:
        for i in (0, 1):
            for j in (0, 1):
                matrix[i, j] *= _tau(i, j, lam, mu, rho)

    total = matrix.sum()
    if total > 0:
        matrix /= total  # renormaliza tras la corrección y el truncamiento
    return matrix


def match_probabilities(lam: float, mu: float, rho: float = 0.0) -> MatchProbabilities:
    """Calcula 1X2, goles esperados y matriz de marcadores."""
    matrix = score_matrix(lam, mu, rho)
    p_home = float(np.tril(matrix, -1).sum())  # home > away
    p_away = float(np.triu(matrix, 1).sum())  # away > home
    p_draw = float(np.trace(matrix))  # home == away

    return MatchProbabilities(
        p_home=p_home,
        p_draw=p_draw,
        p_away=p_away,
        expected_home_goals=lam,
        expected_away_goals=mu,
        score_matrix=matrix,
    )
