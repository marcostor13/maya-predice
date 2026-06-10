"""Tests del parser de wikitexto del proveedor de Wikipedia (puro, sin red)."""

from app.data.players.wikipedia import parse_squad_wikitext

SAMPLE = """
{{Infobox national football team
| name = Argentina
| manager = [[Lionel Scaloni]]
}}
==Current squad==
{{nat fs start}}
{{nat fs player|no=1|pos=GK|name=[[Emiliano Martínez]]|age=...|club=[[Aston Villa]]|clubnat=ENG}}
{{nat fs g player|no=10|pos=FW|name=[[Lionel Andrés Messi|Lionel Messi]]|club=[[Inter Miami]]|clubnat=USA}}
{{nat fs player|no=5|pos=MF|name=[[Enzo Fernández]]|club=[[Chelsea F.C.|Chelsea]]|clubnat=ENG}}
{{nat fs end}}
"""


def test_parses_all_players():
    players, manager = parse_squad_wikitext(SAMPLE)
    assert len(players) == 3
    assert manager == "Lionel Scaloni"


def test_extracts_fields_and_wikilinks():
    players, _ = parse_squad_wikitext(SAMPLE)
    messi = next(p for p in players if p["no"] == 10)
    assert messi["name"] == "Lionel Messi"          # texto visible
    assert messi["title"] == "Lionel Andrés Messi"  # página (para la foto)
    assert messi["pos"] == "FW"
    assert messi["club"] == "Inter Miami"


def test_club_uses_link_target_when_piped():
    players, _ = parse_squad_wikitext(SAMPLE)
    enzo = next(p for p in players if p["no"] == 5)
    assert enzo["club"] == "Chelsea F.C."


def test_empty_wikitext():
    players, manager = parse_squad_wikitext("sin plantillas aquí")
    assert players == []
    assert manager is None
