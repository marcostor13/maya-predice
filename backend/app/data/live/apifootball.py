"""Proveedor de marcadores en vivo vía API-Football / API-SPORTS.

Endpoint `GET /fixtures?live=all`: devuelve los partidos en juego con minuto,
estado corto (1H, HT, 2H, ET, P, FT, AET, PEN…) y goles. Requiere API key
(`APIFOOTBALL_KEY`) y que `v3.football.api-sports.io` esté en la allowlist.

Ligero a propósito: una sola llamada por ciclo (cada ~2 min). Solo nos interesan
partidos del Mundial; si el item trae `league.id`, se filtra por la Copa Mundial.

Docs: https://www.api-football.com/documentation-v3
"""

from __future__ import annotations

from app.data.live._mapping import code_for, parse_kickoff_date
from app.data.live.base import LiveCandidate, LiveFixture, LiveProvider
from app.data.players._http import get_json

LEAGUE_WORLD_CUP = 1  # id de la Copa Mundial en API-Football
FINISHED_STATUSES = {"FT", "AET", "PEN"}


class APIFootballLiveProvider(LiveProvider):
    name = "apifootball"

    def __init__(self, api_key: str, host: str | None = None):
        self.base = (host or "https://v3.football.api-sports.io").rstrip("/")
        self.headers = {"x-apisports-key": api_key}

    async def fetch_live(
        self, candidates: list[LiveCandidate] | None = None
    ) -> list[LiveFixture]:
        data = await get_json(
            f"{self.base}/fixtures", headers=self.headers, params={"live": "all"}
        )
        items = data.get("response") if isinstance(data, dict) else None
        if not items:
            return []

        fixtures: list[LiveFixture] = []
        for item in items:
            league = item.get("league") or {}
            league_id = league.get("id")
            # Si la fuente indica liga y NO es la Copa Mundial, descártalo.
            if league_id is not None and int(league_id) != LEAGUE_WORLD_CUP:
                continue

            fixture = item.get("fixture") or {}
            status = (fixture.get("status") or {})
            teams = item.get("teams") or {}
            goals = item.get("goals") or {}
            home = teams.get("home") or {}
            away = teams.get("away") or {}

            short = (status.get("short") or "").upper()
            home_name = home.get("name")
            away_name = away.get("name")
            fixtures.append(
                LiveFixture(
                    home_code=code_for(home_name),
                    away_code=code_for(away_name),
                    home_name=home_name,
                    away_name=away_name,
                    kickoff_date=parse_kickoff_date(fixture.get("date")),
                    minute=status.get("elapsed"),
                    status=short,
                    home_goals=goals.get("home"),
                    away_goals=goals.get("away"),
                    finished=short in FINISHED_STATUSES,
                )
            )
        return fixtures
