"""Proveedor de marcadores en vivo vía API-Football / API-SPORTS.

Endpoint `GET /fixtures?live=all`: devuelve los partidos en juego con minuto,
estado corto (1H, HT, 2H, ET, P, FT, AET, PEN…) y goles. Requiere API key
(`APIFOOTBALL_KEY`) y que `v3.football.api-sports.io` esté en la allowlist.

Ligero a propósito: una sola llamada por ciclo (cada ~2 min). Solo nos interesan
partidos del Mundial; si el item trae `league.id`, se filtra por la Copa Mundial.

Docs: https://www.api-football.com/documentation-v3
"""

from __future__ import annotations

from datetime import date

from app.data.live.base import LiveFixture, LiveProvider
from app.data.players._http import get_json
from app.data.team_mapping import ALIASES, TEAMS, resolve_team

LEAGUE_WORLD_CUP = 1  # id de la Copa Mundial en API-Football
FINISHED_STATUSES = {"FT", "AET", "PEN"}

# Índice nombre-normalizado -> código (incluye alias del proveedor).
_NAME_TO_CODE: dict[str, str] = {}
for _name, (_code, _conf) in TEAMS.items():
    _NAME_TO_CODE[_name.strip().lower()] = _code
for _alias, _canonical in ALIASES.items():
    _resolved = resolve_team(_canonical)
    if _resolved:
        _NAME_TO_CODE[_alias.strip().lower()] = _resolved[1]


def _code_for(name: str | None) -> str | None:
    if not name:
        return None
    return _NAME_TO_CODE.get(name.strip().lower())


def _parse_kickoff_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        # ISO-8601, p. ej. "2026-06-11T19:00:00+00:00".
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class APIFootballLiveProvider(LiveProvider):
    name = "apifootball"

    def __init__(self, api_key: str, host: str | None = None):
        self.base = (host or "https://v3.football.api-sports.io").rstrip("/")
        self.headers = {"x-apisports-key": api_key}

    async def fetch_live(self) -> list[LiveFixture]:
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
                    home_code=_code_for(home_name),
                    away_code=_code_for(away_name),
                    home_name=home_name,
                    away_name=away_name,
                    kickoff_date=_parse_kickoff_date(fixture.get("date")),
                    minute=status.get("elapsed"),
                    status=short,
                    home_goals=goals.get("home"),
                    away_goals=goals.get("away"),
                    finished=short in FINISHED_STATUSES,
                )
            )
        return fixtures
