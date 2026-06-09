"""Tests del parser de plantillas en formato fixture."""

from app.data.players.localfixture import parse_squads
from app.models.squad import PlayerStatus, Position, SquadRole

SAMPLE = {
    "source": "fixture",
    "squads": [
        {
            "team_code": "ARG",
            "coach": {"name": "Lionel Scaloni", "nationality": "Argentina"},
            "players": [
                {
                    "full_name": "Lionel Messi",
                    "position": "FWD",
                    "shirt_number": 10,
                    "club": "Inter Miami",
                    "role": "starter",
                    "status": "available",
                },
                {
                    "full_name": "Enzo Fernández",
                    "position": "Midfielder",
                    "shirt_number": 24,
                    "role": "substitute",
                    "status": "doubtful",
                },
            ],
        }
    ],
}


def test_parse_squad_basic():
    squads = parse_squads(SAMPLE)
    assert len(squads) == 1
    sq = squads[0]
    assert sq.team_code == "ARG"
    assert sq.coach.name == "Lionel Scaloni"
    assert len(sq.players) == 2


def test_position_and_status_normalized():
    sq = parse_squads(SAMPLE)[0]
    messi = sq.players[0]
    enzo = sq.players[1]
    assert messi.position == Position.FWD
    assert messi.role == SquadRole.STARTER
    assert messi.status == PlayerStatus.AVAILABLE
    assert enzo.position == Position.MID  # "Midfielder" -> MID
    assert enzo.role == SquadRole.SUBSTITUTE
    assert enzo.status == PlayerStatus.DOUBTFUL


def test_source_label_applied():
    squads = parse_squads(SAMPLE, source="mi-fuente")
    assert squads[0].source == "mi-fuente"
    assert squads[0].players[0].source == "mi-fuente"
