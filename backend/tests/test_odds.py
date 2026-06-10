"""Tests del proveedor de cuotas (conversión y parseo, puros y sin red)."""

from app.data.odds.the_odds_api import decimal_to_probabilities, parse_odds_events


def test_decimal_to_probabilities_removes_margin():
    p = decimal_to_probabilities(2.0, 3.5, 4.0)
    assert p is not None
    assert abs(sum(p) - 1.0) < 1e-9          # sin margen: suman 1
    assert p[0] > p[1] > p[2]                 # local favorito (cuota más baja)


def test_decimal_to_probabilities_even_odds():
    p = decimal_to_probabilities(3.0, 3.0, 3.0)
    assert p is not None
    assert all(abs(x - 1 / 3) < 1e-9 for x in p)


def test_decimal_to_probabilities_invalid():
    assert decimal_to_probabilities(0, 3.0, 4.0) is None
    assert decimal_to_probabilities(None, None, None) is None  # type: ignore[arg-type]


def test_parse_odds_events_averages_bookmakers():
    events = [
        {
            "home_team": "Argentina",
            "away_team": "Brazil",
            "bookmakers": [
                {"markets": [{"key": "h2h", "outcomes": [
                    {"name": "Argentina", "price": 2.0},
                    {"name": "Draw", "price": 3.0},
                    {"name": "Brazil", "price": 4.0},
                ]}]},
                {"markets": [{"key": "h2h", "outcomes": [
                    {"name": "Argentina", "price": 2.2},
                    {"name": "Draw", "price": 3.2},
                    {"name": "Brazil", "price": 3.6},
                ]}]},
            ],
        }
    ]
    out = parse_odds_events(events)
    key = ("argentina", "brazil")
    assert key in out
    terna = out[key]
    assert abs(sum(terna) - 1.0) < 1e-9
    assert terna[0] > terna[2]  # Argentina más probable que Brasil


def test_parse_odds_events_ignores_non_h2h_and_empty():
    assert parse_odds_events([]) == {}
    events = [{"home_team": "A", "away_team": "B", "bookmakers": [
        {"markets": [{"key": "totals", "outcomes": []}]}
    ]}]
    assert parse_odds_events(events) == {}
