"""Tests del modelo Dixon-Coles."""

from datetime import date

import pytest

from app.services.prediction.dixon_coles import DixonColesModel, MatchResult


def _sample_matches() -> list[MatchResult]:
    # Equipo A claramente más fuerte que B y C.
    return [
        MatchResult("A", "B", 3, 0, date(2025, 1, 1)),
        MatchResult("A", "C", 2, 0, date(2025, 1, 8)),
        MatchResult("B", "C", 1, 1, date(2025, 1, 15)),
        MatchResult("B", "A", 0, 2, date(2025, 1, 22)),
        MatchResult("C", "A", 0, 3, date(2025, 1, 29)),
        MatchResult("C", "B", 1, 1, date(2025, 2, 5)),
    ]


def test_fit_sets_parameters():
    model = DixonColesModel().fit(_sample_matches())
    assert set(model.attack) == {"A", "B", "C"}
    assert model.home_advantage is not None


def test_stronger_team_has_higher_attack():
    model = DixonColesModel().fit(_sample_matches())
    assert model.attack["A"] > model.attack["B"]
    assert model.attack["A"] > model.attack["C"]


def test_predict_returns_valid_probabilities():
    model = DixonColesModel().fit(_sample_matches())
    probs = model.predict("A", "B")
    total = probs.p_home + probs.p_draw + probs.p_away
    assert abs(total - 1.0) < 1e-6
    assert probs.p_home > probs.p_away  # A es más fuerte y juega de local


def test_unknown_team_raises():
    model = DixonColesModel().fit(_sample_matches())
    with pytest.raises(KeyError):
        model.predict("A", "ZZZ")


def test_serialization_roundtrip():
    model = DixonColesModel().fit(_sample_matches())
    restored = DixonColesModel.from_dict(model.to_dict())
    p1 = model.predict("A", "B")
    p2 = restored.predict("A", "B")
    assert abs(p1.p_home - p2.p_home) < 1e-9
