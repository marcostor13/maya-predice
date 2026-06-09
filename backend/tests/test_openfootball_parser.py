"""Tests del parser de la fuente oficial (openfootball)."""

from app.data.providers.openfootball import parse_matches
from app.models.match import MatchStage

SAMPLE = {
    "name": "World Cup 2026",
    "matches": [
        {
            "round": "Matchday 1",
            "date": "2026-06-11",
            "time": "13:00 UTC-6",
            "team1": "Mexico",
            "team2": "South Africa",
            "group": "Group A",
            "ground": "Mexico City",
        },
        {
            "round": "Final",
            "date": "2026-07-19",
            "time": "15:00 UTC-4",
            "team1": "W101",
            "team2": "W102",
            "ground": "New York/New Jersey (East Rutherford)",
        },
    ],
}


def test_parses_all_matches():
    matches = parse_matches(SAMPLE)
    assert len(matches) == 2


def test_group_match_resolves_real_teams():
    m = parse_matches(SAMPLE)[0]
    assert m.stage == MatchStage.GROUP
    assert m.matchday == 1
    assert m.group == "A"
    assert m.home_code == "MEX"
    assert m.away_code == "RSA"
    assert m.home_placeholder is None


def test_kickoff_converted_to_utc():
    m = parse_matches(SAMPLE)[0]
    # 13:00 en UTC-6 => 19:00 UTC
    assert m.kickoff is not None
    assert m.kickoff.hour == 19
    assert m.kickoff.tzinfo is not None


def test_knockout_match_keeps_placeholders():
    final = parse_matches(SAMPLE)[1]
    assert final.stage == MatchStage.FINAL
    assert final.home_code is None
    assert final.home_placeholder == "W101"
    assert final.away_placeholder == "W102"


def test_external_ref_is_stable_and_distinct():
    matches = parse_matches(SAMPLE)
    refs = [m.external_ref for m in matches]
    assert len(set(refs)) == 2
    # Reparsear produce las mismas claves (idempotencia del upsert).
    assert refs == [m.external_ref for m in parse_matches(SAMPLE)]


def test_score_parsing():
    data = {
        "matches": [
            {
                "round": "Matchday 1",
                "date": "2026-06-11",
                "time": "13:00 UTC-6",
                "team1": "Mexico",
                "team2": "South Africa",
                "group": "Group A",
                "ground": "Mexico City",
                "score": {"ft": [2, 1]},
            }
        ]
    }
    m = parse_matches(data)[0]
    assert m.home_goals == 2
    assert m.away_goals == 1
    assert m.is_finished is True
