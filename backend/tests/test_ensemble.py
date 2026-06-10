"""Tests del ensamble de probabilidades (modelo + fuente externa, estilo Opta)."""

from app.services.prediction.ensemble import best_blend_weight, blend_one


def _close(a, b, eps=1e-9):
    return all(abs(x - y) < eps for x, y in zip(a, b, strict=True))


def test_weight_one_is_model():
    assert _close(blend_one((0.6, 0.3, 0.1), (0.1, 0.2, 0.7), 1.0), (0.6, 0.3, 0.1))


def test_weight_zero_is_external():
    assert _close(blend_one((0.6, 0.3, 0.1), (0.1, 0.2, 0.7), 0.0), (0.1, 0.2, 0.7))


def test_blend_normalizes_to_one():
    p = blend_one((0.5, 0.3, 0.2), (0.2, 0.5, 0.3), 0.5)
    assert abs(sum(p) - 1.0) < 1e-9


def test_blend_is_convex_average():
    # con ω=0.5 cada componente es la media (antes de normalizar ya suman 1)
    p = blend_one((0.6, 0.2, 0.2), (0.2, 0.2, 0.6), 0.5)
    assert abs(p[0] - 0.4) < 1e-9 and abs(p[2] - 0.4) < 1e-9


def test_best_weight_favors_accurate_source():
    # la externa acierta siempre, el modelo se equivoca → ω* debe tender a 0
    model = [(0.8, 0.1, 0.1), (0.1, 0.1, 0.8)]
    ext = [(0.1, 0.1, 0.8), (0.8, 0.1, 0.1)]
    outcomes = ["A", "H"]  # coincide con la externa
    w, score = best_blend_weight(model, ext, outcomes, step=0.1)
    assert w < 0.5
    assert score >= 0.0


def test_best_weight_favors_model_when_better():
    model = [(0.8, 0.1, 0.1), (0.1, 0.1, 0.8)]
    ext = [(0.2, 0.4, 0.4), (0.4, 0.4, 0.2)]
    outcomes = ["H", "A"]  # coincide con el modelo
    w, _ = best_blend_weight(model, ext, outcomes, step=0.1)
    assert w > 0.5


def test_best_weight_empty():
    assert best_blend_weight([], [], []) == (1.0, 0.0)
