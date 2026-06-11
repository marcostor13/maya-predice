"""Tests de los proveedores de marcador en vivo (parseo puro, SIN red).

Cada fuente se prueba con un JSON/HTML de muestra; `get_json` y el cliente httpx
se mockean. No se toca la red.
"""

from __future__ import annotations

import asyncio

import app.data.live.espn as espn_mod
import app.data.live.google as google_mod
import app.data.live.thesportsdb as tsdb_mod
from app.data.live.base import LiveCandidate
from app.data.live.espn import ESPNLiveProvider
from app.data.live.google import GoogleScrapeLiveProvider
from app.data.live.thesportsdb import TheSportsDBLiveProvider

# --- ESPN ----------------------------------------------------------------

_ESPN_SAMPLE = {
    "events": [
        {
            "date": "2026-06-11T19:00Z",
            "competitions": [
                {
                    "status": {
                        "displayClock": "67'",
                        "clock": 67,
                        "type": {"state": "in", "completed": False},
                    },
                    "competitors": [
                        {
                            "homeAway": "home",
                            "score": "1",
                            "team": {"displayName": "Argentina", "abbreviation": "ARG"},
                        },
                        {
                            "homeAway": "away",
                            "score": "0",
                            "team": {"displayName": "Brazil", "abbreviation": "BRA"},
                        },
                    ],
                }
            ],
        },
        {
            "date": "2026-06-11T16:00Z",
            "competitions": [
                {
                    "status": {
                        "displayClock": "90'",
                        "type": {"state": "post", "completed": True},
                    },
                    "competitors": [
                        {
                            "homeAway": "home",
                            "score": "2",
                            "team": {"displayName": "Spain"},
                        },
                        {
                            "homeAway": "away",
                            "score": "3",
                            "team": {"displayName": "France"},
                        },
                    ],
                }
            ],
        },
        {  # "pre": no debe aparecer
            "date": "2026-06-12T19:00Z",
            "competitions": [
                {
                    "status": {"type": {"state": "pre", "completed": False}},
                    "competitors": [
                        {"homeAway": "home", "score": "0", "team": {"displayName": "Mexico"}},
                        {"homeAway": "away", "score": "0", "team": {"displayName": "USA"}},
                    ],
                }
            ],
        },
    ]
}


def test_espn_parses_in_and_post(monkeypatch):
    async def fake_get_json(url, **kwargs):
        return _ESPN_SAMPLE

    monkeypatch.setattr(espn_mod, "get_json", fake_get_json)

    fixtures = asyncio.run(ESPNLiveProvider().fetch_live())
    assert len(fixtures) == 2  # el "pre" se descarta

    live = fixtures[0]
    assert live.home_code == "ARG" and live.away_code == "BRA"
    assert live.minute == 67
    assert live.home_goals == 1 and live.away_goals == 0
    assert live.finished is False

    post = fixtures[1]
    assert post.home_code == "ESP" and post.away_code == "FRA"
    assert post.finished is True
    assert post.minute is None
    assert post.home_goals == 2 and post.away_goals == 3


def test_espn_empty_is_defensive(monkeypatch):
    async def fake_get_json(url, **kwargs):
        return {}

    monkeypatch.setattr(espn_mod, "get_json", fake_get_json)
    assert asyncio.run(ESPNLiveProvider().fetch_live()) == []


# --- TheSportsDB ---------------------------------------------------------

_TSDB_SAMPLE = {
    "livescore": [
        {
            "strHomeTeam": "Argentina",
            "strAwayTeam": "Brazil",
            "intHomeScore": "1",
            "intAwayScore": "1",
            "strProgress": "58",
            "strStatus": "2H",
            "dateEvent": "2026-06-11",
            "strLeague": "FIFA World Cup",
        },
        {  # clubes: no mapea -> descartado
            "strHomeTeam": "Real Madrid",
            "strAwayTeam": "FC Barcelona",
            "intHomeScore": "2",
            "intAwayScore": "0",
            "strProgress": "33",
            "strStatus": "1H",
            "dateEvent": "2026-06-11",
            "strLeague": "Spanish La Liga",
        },
    ]
}


def test_thesportsdb_keeps_nations_drops_clubs(monkeypatch):
    async def fake_get_json(url, **kwargs):
        return _TSDB_SAMPLE

    monkeypatch.setattr(tsdb_mod, "get_json", fake_get_json)

    fixtures = asyncio.run(TheSportsDBLiveProvider("3").fetch_live())
    assert len(fixtures) == 1
    fx = fixtures[0]
    assert fx.home_code == "ARG" and fx.away_code == "BRA"
    assert fx.minute == 58
    assert fx.home_goals == 1 and fx.away_goals == 1
    assert fx.finished is False


def test_thesportsdb_finished_and_events_key(monkeypatch):
    sample = {
        "events": [
            {
                "strHomeTeam": "Spain",
                "strAwayTeam": "France",
                "intHomeScore": "2",
                "intAwayScore": "1",
                "strProgress": "FT",
                "strStatus": "Match Finished",
                "dateEvent": "2026-06-11",
                "strLeague": "World Cup",
            }
        ]
    }

    async def fake_get_json(url, **kwargs):
        return sample

    monkeypatch.setattr(tsdb_mod, "get_json", fake_get_json)
    fixtures = asyncio.run(TheSportsDBLiveProvider().fetch_live())
    assert len(fixtures) == 1
    assert fixtures[0].finished is True
    assert fixtures[0].minute is None


# --- Google scraping -----------------------------------------------------

_CAND = LiveCandidate(
    home_code="ARG",
    away_code="BRA",
    home_name="Argentina",
    away_name="Brazil",
    kickoff_date=None,
)


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeClient:
    def __init__(self, text: str):
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, headers=None):
        return _FakeResponse(self._text)


def _patch_client(monkeypatch, text: str) -> None:
    monkeypatch.setattr(
        google_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient(text)
    )


def test_google_parses_score(monkeypatch):
    html = "<div>Argentina <span>2</span> - <span>1</span> Brazil</div>"
    _patch_client(monkeypatch, html)
    fixtures = asyncio.run(GoogleScrapeLiveProvider().fetch_live([_CAND]))
    assert len(fixtures) == 1
    fx = fixtures[0]
    assert fx.home_code == "ARG" and fx.away_code == "BRA"
    assert fx.home_goals == 2 and fx.away_goals == 1
    assert fx.status == "LIVE" and fx.finished is False


def test_google_garbage_returns_empty(monkeypatch):
    _patch_client(monkeypatch, "<html>sin marcador alguno aqui</html>")
    fixtures = asyncio.run(GoogleScrapeLiveProvider().fetch_live([_CAND]))
    assert fixtures == []


def test_google_no_candidates_is_noop(monkeypatch):
    # Sin candidatos no debe ni tocar el cliente.
    assert asyncio.run(GoogleScrapeLiveProvider().fetch_live(None)) == []
    assert asyncio.run(GoogleScrapeLiveProvider().fetch_live([])) == []
