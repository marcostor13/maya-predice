"""Proveedor de marcadores en vivo vía TheSportsDB (gratis, key de prueba "3").

Endpoint v1 `livescore.php?s=Soccer`: lista los partidos de fútbol en juego. La
respuesta usa `livescore` o `events` según la versión; soportamos ambos. Como
incluye clubes de todo el mundo, filtramos a selecciones del Mundial: aceptamos
un item si su liga menciona "World Cup"/"Mundial" o si AMBOS equipos mapean a un
código FIFA (descartando así los clubes).

Host: `www.thesportsdb.com` (ya allowlistado para plantillas).
"""

from __future__ import annotations

from app.data.live._mapping import code_for, parse_kickoff_date
from app.data.live.base import LiveCandidate, LiveFixture, LiveProvider
from app.data.players._http import get_json

FINISHED_PROGRESS = {"FT", "MATCH FINISHED", "AET", "PEN"}
FINISHED_STATUS = {"MATCH FINISHED"}
_HALFTIME = {"HT", "HALFTIME"}


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_minute(progress: object) -> int | None:
    if progress is None:
        return None
    text = str(progress).strip()
    return int(text) if text.isdigit() else None


def _is_national_match(league: str, home_code: str | None, away_code: str | None) -> bool:
    league_u = (league or "").lower()
    if "world cup" in league_u or "mundial" in league_u:
        return True
    return bool(home_code) and bool(away_code)


class TheSportsDBLiveProvider(LiveProvider):
    name = "thesportsdb"

    def __init__(self, api_key: str = "3"):
        self.api_key = api_key or "3"
        self.base = "https://www.thesportsdb.com/api/v1/json"

    async def fetch_live(
        self, candidates: list[LiveCandidate] | None = None
    ) -> list[LiveFixture]:
        url = f"{self.base}/{self.api_key}/livescore.php"
        data = await get_json(url, params={"s": "Soccer"})
        if not isinstance(data, dict):
            return []
        items = data.get("livescore")
        if items is None:
            items = data.get("events")
        if not items:
            return []

        fixtures: list[LiveFixture] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            home_name = item.get("strHomeTeam")
            away_name = item.get("strAwayTeam")
            home_code = code_for(home_name)
            away_code = code_for(away_name)
            league = item.get("strLeague") or ""
            if not _is_national_match(league, home_code, away_code):
                continue

            progress = item.get("strProgress")
            status = (item.get("strStatus") or "").strip()
            status_u = status.upper()
            progress_u = (str(progress).strip().upper()) if progress else ""
            finished = (
                progress_u in FINISHED_PROGRESS
                or status_u in FINISHED_STATUS
                or status_u in FINISHED_PROGRESS
            )

            minute = None
            if not finished and progress_u not in _HALFTIME:
                minute = _parse_minute(progress)

            fixtures.append(
                LiveFixture(
                    home_code=home_code,
                    away_code=away_code,
                    home_name=home_name,
                    away_name=away_name,
                    kickoff_date=parse_kickoff_date(item.get("dateEvent")),
                    minute=minute,
                    status=status or progress_u,
                    home_goals=_to_int(item.get("intHomeScore")),
                    away_goals=_to_int(item.get("intAwayScore")),
                    finished=finished,
                )
            )
        return fixtures
