"""Tests de las métricas de evaluación de predicciones."""

import math

from app.services.prediction.metrics import accuracy, brier_score, log_loss, rps


def test_rps_perfect_is_zero():
    assert rps([(1.0, 0.0, 0.0)], ["H"]) == 0.0


def test_rps_penalizes_far_more_than_near():
    # gana el visitante (A); predecir local (lejos) debe puntuar peor que empate (cerca)
    far = rps([(1.0, 0.0, 0.0)], ["A"])   # dijo local, ganó visitante
    near = rps([(0.0, 1.0, 0.0)], ["A"])  # dijo empate, ganó visitante
    assert far > near > 0


def test_rps_known_value():
    # uniforme con resultado local: CP=(1/3,2/3); CE=(1,1) -> ((1/3-1)^2+(2/3-1)^2)/2
    expected = ((1 / 3 - 1) ** 2 + (2 / 3 - 1) ** 2) / 2
    assert abs(rps([(1 / 3, 1 / 3, 1 / 3)], ["H"]) - expected) < 1e-9


def test_rps_empty():
    assert rps([], []) == 0.0


def test_perfect_prediction_zero_loss():
    probs = [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)]
    outcomes = ["H", "A"]
    assert log_loss(probs, outcomes) < 1e-6
    assert brier_score(probs, outcomes) < 1e-12
    assert accuracy(probs, outcomes) == 1.0


def test_log_loss_known_value():
    # una sola predicción con 0.5 al resultado correcto -> -ln(0.5)
    assert abs(log_loss([(0.5, 0.3, 0.2)], ["H"]) - math.log(2)) < 1e-9


def test_confident_wrong_is_penalized():
    good = log_loss([(0.6, 0.3, 0.1)], ["H"])
    bad = log_loss([(0.05, 0.15, 0.8)], ["H"])
    assert bad > good


def test_brier_uniform():
    # terna uniforme con resultado H: (1/3-1)^2 + (1/3)^2 + (1/3)^2
    expected = (1 / 3 - 1) ** 2 + (1 / 3) ** 2 + (1 / 3) ** 2
    assert abs(brier_score([(1 / 3, 1 / 3, 1 / 3)], ["H"]) - expected) < 1e-9


def test_accuracy_picks_argmax():
    probs = [(0.5, 0.3, 0.2), (0.2, 0.3, 0.5), (0.1, 0.8, 0.1)]
    outcomes = ["H", "H", "D"]  # acierta 1.º y 3.º, falla 2.º
    assert abs(accuracy(probs, outcomes) - 2 / 3) < 1e-9


def test_empty_is_zero():
    assert log_loss([], []) == 0.0
    assert brier_score([], []) == 0.0
    assert accuracy([], []) == 0.0
