"""Tests del cálculo de Elo y su conversión a prior."""

from datetime import date

from app.services.prediction.dixon_coles import MatchResult
from app.services.prediction.elo import compute_elo, elo_to_priors


def test_winner_gains_loser_loses():
    matches = [MatchResult("A", "B", 3, 0, date(2025, 1, 1), neutral=True)]
    elo = compute_elo(matches)
    assert elo["A"] > 1500 > elo["B"]
    # Elo es de suma cero alrededor de la base en un único partido neutral
    assert abs((elo["A"] - 1500) + (elo["B"] - 1500)) < 1e-6


def test_consistent_winner_ranks_higher():
    matches = [
        MatchResult("A", "B", 2, 0, date(2025, 1, 1), neutral=True),
        MatchResult("B", "C", 2, 0, date(2025, 1, 8), neutral=True),
        MatchResult("A", "C", 3, 0, date(2025, 1, 15), neutral=True),
        MatchResult("C", "A", 0, 1, date(2025, 1, 22), neutral=True),
    ]
    elo = compute_elo(matches)
    assert elo["A"] > elo["B"] > elo["C"]


def test_bigger_win_moves_more():
    narrow = compute_elo([MatchResult("A", "B", 1, 0, date(2025, 1, 1), neutral=True)])
    blowout = compute_elo([MatchResult("A", "B", 5, 0, date(2025, 1, 1), neutral=True)])
    assert blowout["A"] > narrow["A"]  # goleada mueve más el Elo


def test_priors_centered_and_scaled():
    elo = {"A": 1700.0, "B": 1500.0, "C": 1300.0}
    priors = elo_to_priors(elo, scale=0.5)
    assert abs(sum(priors.values())) < 1e-9  # media 0
    assert priors["A"] > 0 > priors["C"]


def test_empty_inputs():
    assert compute_elo([]) == {}
    assert elo_to_priors({}) == {}
