"""Tests de la integración modelo Dixon-Coles + ajuste por disponibilidad."""

from datetime import date

from app.services.prediction.availability import (
    AvailabilityConfig,
    PlayerImpact,
    compute_team_adjustment,
)
from app.models.squad import PlayerStatus, Position, SquadRole
from app.services.prediction.dixon_coles import DixonColesModel, MatchResult


def _model() -> DixonColesModel:
    # A fuerte, B medio, C débil; incluye partidos en sede neutral.
    matches = [
        MatchResult("A", "B", 3, 0, date(2025, 1, 1)),
        MatchResult("A", "C", 4, 0, date(2025, 1, 8), neutral=True),
        MatchResult("B", "C", 2, 1, date(2025, 1, 15)),
        MatchResult("B", "A", 0, 2, date(2025, 1, 22)),
        MatchResult("C", "A", 0, 3, date(2025, 1, 29), neutral=True),
        MatchResult("C", "B", 1, 2, date(2025, 2, 5)),
    ]
    return DixonColesModel().fit(matches)


def test_neutral_removes_home_advantage():
    model = _model()
    lam_home, _ = model.expected_goals("A", "B", neutral=False)
    lam_neutral, _ = model.expected_goals("A", "B", neutral=True)
    # con ventaja de localía positiva, el local marca más en cancha propia
    assert lam_home >= lam_neutral


def test_injuries_lower_expected_goals():
    model = _model()
    base = model.predict("A", "B", neutral=True)

    # A pierde a sus delanteros titulares -> menos goles esperados de A
    squad = [
        PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.INJURED),
        PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.OUT),
        PlayerImpact(Position.MID, SquadRole.STARTER, PlayerStatus.AVAILABLE),
        PlayerImpact(Position.DEF, SquadRole.STARTER, PlayerStatus.AVAILABLE),
        PlayerImpact(Position.GK, SquadRole.STARTER, PlayerStatus.AVAILABLE),
    ]
    adj, _ = compute_team_adjustment(squad, AvailabilityConfig(adj_strength=0.6))
    weakened = model.predict("A", "B", neutral=True, home_adj=adj)

    assert weakened.expected_home_goals < base.expected_home_goals
    assert weakened.p_home < base.p_home  # A es menos favorito con bajas


def test_full_squad_matches_unadjusted():
    model = _model()
    base = model.predict("A", "B", neutral=True)
    full = [PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.AVAILABLE)]
    adj, _ = compute_team_adjustment(full)
    same = model.predict("A", "B", neutral=True, home_adj=adj)
    assert abs(same.expected_home_goals - base.expected_home_goals) < 1e-9
