"""Tests de la detección de cambios de la sincronización (función pura)."""

from app.services.sync_service import compute_changes


def _state(**overrides) -> dict:
    base = {
        "kickoff": "2026-06-11T19:00:00+00:00",
        "venue": "Mexico City",
        "matchday": 1,
        "group": "Group A",
        "stage": "group",
        "home_code": "MEX",
        "away_code": "RSA",
        "home_placeholder": None,
        "away_placeholder": None,
        "home_goals": None,
        "away_goals": None,
        "status": "scheduled",
    }
    base.update(overrides)
    return base


def test_new_match_reports_no_field_changes():
    assert compute_changes(None, _state()) == []


def test_no_change_returns_empty():
    assert compute_changes(_state(), _state()) == []


def test_score_change_detected():
    old = _state()
    new = _state(home_goals=2, away_goals=1, status="finished")
    changes = dict((f, (o, n)) for f, o, n in compute_changes(old, new))
    assert "home_goals" in changes
    assert "away_goals" in changes
    assert "status" in changes
    assert changes["home_goals"] == (None, "2")


def test_venue_and_kickoff_change_detected():
    old = _state()
    new = _state(venue="Atlanta", kickoff="2026-06-11T20:00:00+00:00")
    fields = {f for f, _, _ in compute_changes(old, new)}
    assert fields == {"venue", "kickoff"}


def test_placeholder_resolution_detected():
    # Un cruce eliminatorio resuelve su placeholder a una selección real.
    old = _state(stage="final", home_code=None, home_placeholder="W101", group=None, matchday=None)
    new = _state(stage="final", home_code="FRA", home_placeholder=None, group=None, matchday=None)
    fields = {f for f, _, _ in compute_changes(old, new)}
    assert "home_code" in fields
    assert "home_placeholder" in fields
