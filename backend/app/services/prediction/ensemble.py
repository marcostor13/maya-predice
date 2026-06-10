"""Ensamble de probabilidades 1X2 con una fuente externa (mercado / Power Rankings).

La práctica que mejor precisión da —y la que usa el **supercomputador de Opta**—
es **mezclar** el modelo propio con una señal externa muy informativa (las cuotas
del mercado o un rating tipo Power Rankings) en lugar de fiarse de una sola fuente:

    P_final = normalizar( ω · P_modelo + (1−ω) · P_externa )

con `ω ∈ [0,1]` elegido para **minimizar el RPS** en validación (típicamente el
mercado pesa más). Esta mecánica es pura y testeable, e independiente de la fuente:
basta pasarle ternas (p_home, p_draw, p_away). El proveedor de la señal externa se
conecta aparte (API de cuotas, Power Rankings, valor de mercado).
"""

from __future__ import annotations

from app.services.prediction.metrics import rps

Triple = tuple[float, float, float]


def blend_one(model: Triple, ext: Triple, weight: float) -> Triple:
    """Mezcla una terna del modelo con la externa y renormaliza a suma 1."""
    w = min(1.0, max(0.0, weight))
    mixed = [w * m + (1.0 - w) * e for m, e in zip(model, ext, strict=True)]
    total = sum(mixed) or 1.0
    return (mixed[0] / total, mixed[1] / total, mixed[2] / total)


def blend(model_probs: list[Triple], ext_probs: list[Triple], weight: float) -> list[Triple]:
    """Aplica el ensamble a una lista de predicciones (modelo vs externa)."""
    return [blend_one(m, e, weight) for m, e in zip(model_probs, ext_probs, strict=True)]


def best_blend_weight(
    model_probs: list[Triple],
    ext_probs: list[Triple],
    outcomes: list[str],
    *,
    step: float = 0.05,
) -> tuple[float, float]:
    """Busca el `ω` que minimiza el RPS del ensamble (grid en [0,1]).

    Devuelve `(ω*, rps*)`. `ω=1` = solo modelo; `ω=0` = solo la fuente externa.
    """
    if not model_probs:
        return (1.0, 0.0)
    best_w, best = 1.0, float("inf")
    steps = int(round(1.0 / step))
    for i in range(steps + 1):
        w = i * step
        score = rps(blend(model_probs, ext_probs, weight=w), outcomes)
        if score < best:
            best, best_w = score, w
    return best_w, best
