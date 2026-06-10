"""Proveedor TheSportsDB (fuente 1 de 3).

API gratuita (clave de prueba "3"). Aporta jugadores, posición, dorsal, fecha de
nacimiento y club. Requiere que `www.thesportsdb.com` esté en la allowlist de red
del entorno (en este sandbox de desarrollo NO lo está; sí en producción si se
configura). Ver DEVLOG.md.

Docs: https://www.thesportsdb.com/free_sports_api
"""

from __future__ import annotations

import asyncio

from app.data.players._http import get_json
from app.data.players.base import (
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
    normalize_position,
)
from app.data.team_mapping import TEAMS

# Nombre del equipo en TheSportsDB suele ser "<País>". Para selecciones a veces es
# "<País>" a secas; este mapa permite sobreescribir nombres divergentes.
TEAM_QUERY_OVERRIDES = {"USA": "United States", "South Korea": "South Korea"}


class TheSportsDBProvider(PlayerDataProvider):
    name = "thesportsdb"

    def __init__(self, api_key: str = "3", base: str | None = None, throttle: float = 1.5):
        self.base = (base or "https://www.thesportsdb.com").rstrip("/")
        self.api_key = api_key
        self.throttle = throttle  # segundos entre equipos (la key gratuita es muy limitada)

    async def _team_id(self, team_name: str) -> str | None:
        query = TEAM_QUERY_OVERRIDES.get(team_name, team_name)
        data = await get_json(
            f"{self.base}/api/v1/json/{self.api_key}/searchteams.php", params={"t": query}
        )
        for t in data.get("teams") or []:
            if (t.get("strSport") == "Soccer") and t.get("idTeam"):
                return t["idTeam"]
        return None

    async def _players(self, team_id: str, code: str) -> list[PlayerObservation]:
        data = await get_json(
            f"{self.base}/api/v1/json/{self.api_key}/lookup_all_players.php",
            params={"id": team_id},
        )
        out: list[PlayerObservation] = []
        for p in data.get("player") or []:
            name = p.get("strPlayer")
            if not name:
                continue
            number = p.get("strNumber")
            out.append(
                PlayerObservation(
                    source=self.name,
                    full_name=name,
                    position=normalize_position(p.get("strPosition")),
                    shirt_number=int(number) if (number or "").isdigit() else None,
                    club=p.get("strTeam2") or None,
                )
            )
        return out

    async def fetch_all(self) -> list[SquadObservation]:
        squads: list[SquadObservation] = []
        for team_name, (code, _conf) in TEAMS.items():
            try:
                team_id = await self._team_id(team_name)
                if not team_id:
                    continue
                players = await self._players(team_id, code)
            except RuntimeError:
                continue  # rate limit u otro fallo puntual: salta este equipo
            if players:
                squads.append(
                    SquadObservation(source=self.name, team_code=code, coach=None, players=players)
                )
            # La key gratuita ("3") es muy limitada: pausa para no disparar 429.
            await asyncio.sleep(self.throttle)
        return squads
