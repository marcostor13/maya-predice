"""Tests del módulo Poisson / matriz de marcadores."""

import numpy as np

from app.services.prediction.poisson import match_probabilities, score_matrix


def test_score_matrix_sums_to_one():
    matrix = score_matrix(1.5, 1.2)
    assert np.isclose(matrix.sum(), 1.0, atol=1e-9)


def test_probabilities_sum_to_one():
    probs = match_probabilities(1.5, 1.2)
    total = probs.p_home + probs.p_draw + probs.p_away
    assert np.isclose(total, 1.0, atol=1e-9)


def test_stronger_home_team_more_likely_to_win():
    probs = match_probabilities(2.5, 0.5)
    assert probs.p_home > probs.p_away
    assert probs.p_home > probs.p_draw


def test_dixon_coles_correction_changes_low_scores():
    base = score_matrix(1.0, 1.0, rho=0.0)
    corrected = score_matrix(1.0, 1.0, rho=-0.1)
    # La corrección modifica los marcadores bajos (0-0, 1-1, etc.)
    assert not np.isclose(base[0, 0], corrected[0, 0])


def test_top_scorelines_sorted():
    probs = match_probabilities(1.5, 1.2)
    top = probs.top_scorelines(5)
    assert len(top) == 5
    probs_list = [s["prob"] for s in top]
    assert probs_list == sorted(probs_list, reverse=True)
