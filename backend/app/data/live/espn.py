"""Proveedor de marcadores en vivo vía ESPN (gratis, sin API key).

FUENTE PRINCIPAL. Endpoint público del scoreboard de la Copa Mundial FIFA:
`GET .../soccer/fifa.world/scoreboard`. Devuelve los eventos del día con estado
(pre/in/post), marcador y reloj. No necesita clave.

Solo emite fixtures de partidos en juego ("in") o terminados ("post"); los que
aún no empezaron ("pre") se ignoran. Defensivo: ante cualquier estructura
inesperada devuelve [].

Host a allowlistar en producción: `site.api.espn.com`.
"""

from __future__ import annotations

from app.data.live._mapping import code_for, parse_kickoff_date
from app.data.live.base import LiveCandidate, LiveFixture, LiveProvider
from app.data.players._http import get_json

SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_minute(status: dict) -> int | None:
    """Extrae el minuto desde `displayClock` ("67'") o `clock` (número)."""
    display = status.get("displayClock")
    if isinstance(display, str):
        cleaned = display.replace("'", "").replace("+", "").strip()
        # En descanso ESPN suele dar "HT"/"Halftime" -> no es numérico.
        if cleaned.isdigit():
            return int(cleaned)
    clock = status.get("clock")
    minute = _to_int(clock)
    # `clock` puede venir en segundos; si es muy grande, conviértelo a minutos.
    if minute is not None and minute > 130:
        return minute // 60
    return minute


class ESPNLiveProvider(LiveProvider):
    name = "espn"

    async def fetch_live(
        self, candidates: list[LiveCandidate] | None = None
    ) -> list[LiveFixture]:
        data = await get_json(SCOREBOARD_URL)
        events = data.get("events") if isinstance(data, dict) else None
        if not events:
            return []

        fixtures: list[LiveFixture] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            competitions = event.get("competitions") or []
            if not competitions:
                continue
            comp = competitions[0] or {}
            competitors = comp.get("competitors") or []

            home: dict = {}
            away: dict = {}
            for c in competitors:
                if not isinstance(c, dict):
                    continue
                if c.get("homeAway") == "home":
                    home = c
                elif c.get("homeAway") == "away":
                    away = c
            if not home or not away:
                continue

            status = ((comp.get("status") or {}).get("type")) or {}
            # El reloj/minuto vive en status (no en status.type).
            status_block = comp.get("status") or {}
            state = (status.get("state") or "").lower()
            if state not in ("in", "post"):
                continue
            completed = bool(status.get("completed"))
            finished = state == "post" or completed

            home_team = home.get("team") or {}
            away_team = away.get("team") or {}
            home_name = home_team.get("displayName") or home_team.get("abbreviation")
            away_name = away_team.get("displayName") or away_team.get("abbreviation")

            minute = None if finished else _parse_minute(status_block)

            fixtures.append(
                LiveFixture(
                    home_code=code_for(home_name),
                    away_code=code_for(away_name),
                    home_name=home_name,
                    away_name=away_name,
                    kickoff_date=parse_kickoff_date(event.get("date")),
                    minute=minute,
                    status=(status.get("state") or "").upper(),
                    home_goals=_to_int(home.get("score")),
                    away_goals=_to_int(away.get("score")),
                    finished=finished,
                )
            )
        return fixtures
