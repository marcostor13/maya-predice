"""Tests del parser del histórico de resultados internacionales."""

from app.data.history import parse_results

CSV = """date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
2017-06-01,Brazil,Argentina,2,1,Friendly,Melbourne,Australia,TRUE
2019-07-07,Brazil,Peru,3,1,Copa America,Rio de Janeiro,Brazil,FALSE
2021-06-10,Argentina,Chile,1,1,Friendly,Santiago,Chile,FALSE
2024-06-20,Spain,Bosnia and Herzegovina,2,0,Friendly,Madrid,Spain,FALSE
2026-06-27,Panama,England,NA,NA,FIFA World Cup,East Rutherford,United States,TRUE
"""


def test_filters_by_year():
    results = parse_results(CSV, since_year=2018, team_filter="all")
    # excluye el de 2017 y el partido sin marcador (NA) de 2026
    dates = sorted(str(r.played_on) for r in results)
    assert "2017-06-01" not in dates
    assert all("NA" not in str(r.home_goals) for r in results)


def test_both_filter_keeps_only_known_pairs():
    results = parse_results(CSV, since_year=2010, team_filter="both")
    # Brazil-Argentina (ambos en 48) y Spain-Bosnia (alias) sí; Brazil-Peru no (Perú no clasificó)
    pairs = {(r.home, r.away) for r in results}
    assert ("BRA", "ARG") in pairs
    assert ("ESP", "BIH") in pairs  # alias "Bosnia and Herzegovina"
    assert ("BRA", "PER") not in pairs  # Peru no está entre las 48


def test_any_filter_includes_mixed_matches():
    results = parse_results(CSV, since_year=2010, team_filter="any")
    pairs = {(r.home, r.away) for r in results}
    # Brazil-Peru: Brasil conocido -> code BRA, Peru se conserva por nombre
    assert ("BRA", "Peru") in pairs


def test_neutral_flag_parsed():
    results = parse_results(CSV, since_year=2010, team_filter="both")
    bra_arg = next(r for r in results if r.home == "BRA" and r.away == "ARG")
    assert bra_arg.neutral is True


def test_skips_unplayed_future_matches():
    results = parse_results(CSV, since_year=2010, team_filter="all")
    assert all(r.played_on.year < 2026 for r in results)


def test_match_importance_weighting():
    results = parse_results(CSV, since_year=2010, team_filter="all")
    by_pair = {(r.home, r.away): r for r in results}
    # amistoso pesa menos; partido de torneo (Copa America) pesa más
    assert by_pair[("BRA", "ARG")].importance == 0.5  # Friendly
    assert by_pair[("BRA", "Peru")].importance == 1.5  # Copa America (fase final)
