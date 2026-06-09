"""Proveedor API-Football / API-SPORTS (fuente 2 de 3).

Aporta plantilla (squad), posición, dorsal, edad, entrenador y, vía el endpoint
de lesiones, el estado de cada jugador. Requiere API key (`APIFOOTBALL_KEY`) y que
`v3.football.api-sports.io` esté en la allowlist del entorno. Ver DEVLOG.md.

Docs: https://www.api-football.com/documentation-v3
"""

from __future__ import annotations

from app.data.players._http import get_json
from app.data.players.base import (
    CoachObservation,
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
    normalize_position,
    normalize_status,
)
from app.data.team_mapping import TEAMS

LEAGUE_WORLD_CUP = 1  # id de la Copa Mundial en API-Football
SEASON = 2026


class APIFootballProvider(PlayerDataProvider):
    name = "apifootball"

    def __init__(self, api_key: str, host: str | None = None):
        self.base = (host or "https://v3.football.api-sports.io").rstrip("/")
        self.headers = {"x-apisports-key": api_key}

    async def _team_id(self, team_name: str) -> int | None:
        data = await get_json(
            f"{self.base}/teams", headers=self.headers, params={"search": team_name}
        )
        for item in data.get("response") or []:
            team = item.get("team") or {}
            if team.get("national") and team.get("id"):
                return int(team["id"])
        return None

    async def _injuries(self, team_id: int) -> dict[str, str]:
        """name_lower -> status, según el endpoint de lesiones/sanciones."""
        try:
            data = await get_json(
                f"{self.base}/injuries",
                headers=self.headers,
                params={"team": team_id, "season": SEASON},
            )
        except RuntimeError:
            return {}
        result: dict[str, str] = {}
        for item in data.get("response") or []:
            player = item.get("player") or {}
            name = (player.get("name") or "").lower()
            if name:
                result[name] = player.get("type") or "injured"
        return result

    async def _squad(self, team_id: int) -> tuple[list[PlayerObservation], CoachObservation | None]:
        data = await get_json(
            f"{self.base}/players/squads", headers=self.headers, params={"team": team_id}
        )
        injuries = await self._injuries(team_id)
        players: list[PlayerObservation] = []
        for block in data.get("response") or []:
            for p in block.get("players") or []:
                name = p.get("name")
                if not name:
                    continue
                status = normalize_status(injuries.get(name.lower(), "available"))
                players.append(
                    PlayerObservation(
                        source=self.name,
                        full_name=name,
                        position=normalize_position(p.get("position")),
                        shirt_number=p.get("number"),
                        status=status,
                    )
                )

        coach = None
        try:
            cdata = await get_json(
                f"{self.base}/coachs", headers=self.headers, params={"team": team_id}
            )
            for c in cdata.get("response") or []:
                if c.get("name"):
                    coach = CoachObservation(
                        source=self.name,
                        name=c["name"],
                        nationality=(c.get("nationality")),
                    )
                    break
        except RuntimeError:
            pass
        return players, coach

    async def fetch_all(self) -> list[SquadObservation]:
        squads: list[SquadObservation] = []
        for team_name, (code, _conf) in TEAMS.items():
            team_id = await self._team_id(team_name)
            if not team_id:
                continue
            players, coach = await self._squad(team_id)
            if players or coach:
                squads.append(
                    SquadObservation(
                        source=self.name, team_code=code, coach=coach, players=players
                    )
                )
        return squads
