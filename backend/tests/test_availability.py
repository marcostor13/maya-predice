"""Tests del ajuste por disponibilidad de jugadores (función pura)."""

from app.models.squad import PlayerStatus, Position, SquadRole
from app.services.prediction.availability import (
    AvailabilityConfig,
    PlayerImpact,
    compute_team_adjustment,
    compute_team_availability,
)


def _full_squad() -> list[PlayerImpact]:
    return [
        PlayerImpact(Position.GK, SquadRole.STARTER, PlayerStatus.AVAILABLE),
        PlayerImpact(Position.DEF, SquadRole.STARTER, PlayerStatus.AVAILABLE),
        PlayerImpact(Position.MID, SquadRole.STARTER, PlayerStatus.AVAILABLE),
        PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.AVAILABLE),
    ]


def test_full_squad_has_no_adjustment():
    adj, av = compute_team_adjustment(_full_squad())
    assert av.attack_availability == 1.0
    assert av.defense_availability == 1.0
    assert adj.attack_delta == 0.0
    assert adj.defense_delta == 0.0


def test_injured_forward_reduces_attack_more_than_defense():
    squad = _full_squad()
    squad[3] = PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.INJURED)
    adj, av = compute_team_adjustment(squad)
    assert av.attack_availability < 1.0
    assert adj.attack_delta < 0.0
    # un delantero pesa poco en defensa -> defensa casi intacta
    assert av.defense_availability > av.attack_availability


def test_suspended_goalkeeper_hits_defense():
    squad = _full_squad()
    squad[0] = PlayerImpact(Position.GK, SquadRole.STARTER, PlayerStatus.SUSPENDED)
    adj, av = compute_team_adjustment(squad)
    assert av.defense_availability < 1.0
    assert adj.defense_delta < 0.0
    assert av.attack_availability == 1.0  # el portero no aporta a ataque


def test_doubtful_is_partial():
    squad = _full_squad()
    squad[3] = PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.DOUBTFUL)
    _, av_doubt = compute_team_adjustment(squad)
    squad[3] = PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.INJURED)
    _, av_out = compute_team_adjustment(squad)
    # una duda penaliza menos que una baja total
    assert av_out.attack_availability < av_doubt.attack_availability < 1.0


def test_substitute_weighs_less_than_starter():
    starter_out = _full_squad()
    starter_out[3] = PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.INJURED)
    sub_out = _full_squad() + [
        PlayerImpact(Position.FWD, SquadRole.SUBSTITUTE, PlayerStatus.INJURED)
    ]
    _, av_starter = compute_team_adjustment(starter_out)
    _, av_sub = compute_team_adjustment(sub_out)
    # perder un titular pega más que perder un suplente
    assert av_starter.attack_availability < av_sub.attack_availability


def test_adj_strength_scales_delta():
    squad = _full_squad()
    squad[3] = PlayerImpact(Position.FWD, SquadRole.STARTER, PlayerStatus.OUT)
    weak = compute_team_adjustment(squad, AvailabilityConfig(adj_strength=0.2))[0]
    strong = compute_team_adjustment(squad, AvailabilityConfig(adj_strength=0.8))[0]
    assert strong.attack_delta < weak.attack_delta < 0.0


def test_empty_squad_is_neutral():
    av = compute_team_availability([])
    assert av.attack_availability == 1.0
    assert av.defense_availability == 1.0
