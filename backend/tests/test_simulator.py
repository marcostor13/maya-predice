"""Tests del simulador Monte Carlo del torneo."""

from datetime import date
from itertools import combinations

import numpy as np

from app.services.prediction.dixon_coles import DixonColesModel, MatchResult
from app.services.prediction.simulator import TournamentSimulator

TEAMS = ["A", "B", "C", "D", "E", "F"]  # jerarquía decreciente A > … > F


def _model() -> DixonColesModel:
    # Round-robin donde el equipo mejor clasificado gana por más diferencia.
    matches = []
    day = 1
    for i, j in combinations(range(len(TEAMS)), 2):
        margin = (j - i)  # cuanto más separados, mayor diferencia
        matches.append(
            MatchResult(TEAMS[i], TEAMS[j], 1 + margin, 0, date(2025, 1, day), neutral=True)
        )
        day += 1
    return DixonColesModel().fit(matches)


def test_probabilities_in_range_and_one_champion():
    model = _model()
    sim = TournamentSimulator(model, rng=np.random.default_rng(42))
    groups = {"G1": ["A", "B", "C"], "G2": ["D", "E", "F"]}
    probs = sim.run(groups, iterations=300)

    for p in probs.values():
        for v in p.values():
            assert 0.0 <= v <= 1.0
    total_champion = sum(p["champion"] for p in probs.values())
    assert abs(total_champion - 1.0) < 1e-6  # exactamente un campeón por torneo


def test_stronger_team_more_likely_champion():
    model = _model()
    sim = TournamentSimulator(model, rng=np.random.default_rng(7))
    groups = {"G1": ["A", "F"], "G2": ["B", "E"]}
    probs = sim.run(groups, iterations=500)
    assert probs["A"]["champion"] > probs["E"]["champion"]


def test_monotonic_stage_probabilities():
    model = _model()
    sim = TournamentSimulator(model, rng=np.random.default_rng(1))
    groups = {"G1": ["A", "B", "C"], "G2": ["D", "E", "F"]}
    probs = sim.run(groups, iterations=300)
    a = probs["A"]
    # cuanto más profunda la ronda, menor (o igual) la probabilidad
    assert a["advance"] >= a["quarter"] >= a["semi"] >= a["final"] >= a["champion"]
