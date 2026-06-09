"""Métricas de evaluación de predicciones 1X2 (puras, testeables).

Las predicciones son ternas de probabilidad (p_home, p_draw, p_away) que suman 1;
el resultado real es uno de "H" (local), "D" (empate) o "A" (visitante).

- **log-loss**: penaliza con dureza la confianza equivocada (menor = mejor).
- **Brier (multiclase)**: error cuadrático medio de las probabilidades.
- **accuracy**: acierto del resultado más probable.
"""

from __future__ import annotations

import math

OUTCOMES = ("H", "D", "A")


def _clip(p: float, eps: float = 1e-12) -> float:
    return min(1.0 - eps, max(eps, p))


def log_loss(probs: list[tuple[float, float, float]], outcomes: list[str]) -> float:
    if not probs:
        return 0.0
    total = 0.0
    for (ph, pd, pa), y in zip(probs, outcomes, strict=True):
        p = {"H": ph, "D": pd, "A": pa}[y]
        total += -math.log(_clip(p))
    return total / len(probs)


def brier_score(probs: list[tuple[float, float, float]], outcomes: list[str]) -> float:
    if not probs:
        return 0.0
    total = 0.0
    for (ph, pd, pa), y in zip(probs, outcomes, strict=True):
        target = (1.0 if y == "H" else 0.0, 1.0 if y == "D" else 0.0, 1.0 if y == "A" else 0.0)
        total += (ph - target[0]) ** 2 + (pd - target[1]) ** 2 + (pa - target[2]) ** 2
    return total / len(probs)


def accuracy(probs: list[tuple[float, float, float]], outcomes: list[str]) -> float:
    if not probs:
        return 0.0
    hits = 0
    for (ph, pd, pa), y in zip(probs, outcomes, strict=True):
        pred = OUTCOMES[max(range(3), key=lambda i: (ph, pd, pa)[i])]
        hits += int(pred == y)
    return hits / len(probs)
