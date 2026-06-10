"""Proveedor Sportmonks (plantillas y jugadores).

API de pago (token en `SPAPI_TOKEN`). Cada llamada pasa por la **caché en base de
datos** (`cached_get_json`): una misma consulta no se repite, para ahorrar
créditos. Requiere que `api.sportmonks.com` esté en la allowlist del entorno.

Docs: https://docs.sportmonks.com/football
"""

from __future__ import annotations

import asyncio
from datetime import date
from urllib.parse import quote

from app.data.players._cache import cached_get_json
from app.data.players.base import (
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
    normalize_position,
)
from app.data.team_mapping import TEAMS

BASE = "https://api.sportmonks.com/v3/football"

# Nombre de la selección en Sportmonks (suele ser el país en inglés).
TEAM_QUERY = {"USA": "United States", "South Korea": "South Korea", "Ivory Coast": "Ivory Coast"}


def _birth_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class SportmonksProvider(PlayerDataProvider):
    name = "sportmonks"

    def __init__(self, token: str, base: str | None = None, ttl_hours: int = 24, throttle: float = 0.3):
        self.token = token
        self.base = (base or BASE).rstrip("/")
        self.ttl_hours = ttl_hours
        self.throttle = throttle
        self._headers = {"Authorization": token, "Accept": "application/json"}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        # clave de caché: endpoint + params ordenados (sin token)
        key = "sportmonks:" + path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return await cached_get_json(
            f"{self.base}{path}",
            cache_key=key,
            source="sportmonks",
            params=params,
            headers=self._headers,
            ttl_hours=self.ttl_hours,
        )

    async def _team_id(self, team_name: str) -> int | None:
        query = TEAM_QUERY.get(team_name, team_name)
        data = await self._get(f"/teams/search/{quote(query)}")
        results = data.get("data") or []
        # Preferir selección nacional; si no hay flag, el nombre exacto del país.
        for t in results:
            if t.get("national_team") and t.get("id"):
                return int(t["id"])
        for t in results:
            if (t.get("name") or "").lower() == query.lower() and t.get("id"):
                return int(t["id"])
        return int(results[0]["id"]) if results and results[0].get("id") else None

    async def _squad(self, team_id: int) -> list[PlayerObservation]:
        data = await self._get(
            f"/squads/teams/{team_id}", params={"include": "player.position"}
        )
        players: list[PlayerObservation] = []
        for entry in data.get("data") or []:
            p = entry.get("player") or {}
            name = p.get("display_name") or p.get("name")
            if not name:
                continue
            pos = (p.get("position") or {}).get("name")
            number = entry.get("jersey_number")
            players.append(
                PlayerObservation(
                    source=self.name,
                    full_name=name,
                    position=normalize_position(pos),
                    shirt_number=int(number) if number else None,
                    birth_date=_birth_date(p.get("date_of_birth")),
                )
            )
        return players

    async def fetch_all(self) -> list[SquadObservation]:
        squads: list[SquadObservation] = []
        for team_name, (code, _conf) in TEAMS.items():
            try:
                team_id = await self._team_id(team_name)
                if not team_id:
                    continue
                players = await self._squad(team_id)
            except RuntimeError:
                continue  # fallo puntual de una selección: no aborta el resto
            if players:
                squads.append(
                    SquadObservation(source=self.name, team_code=code, coach=None, players=players)
                )
            await asyncio.sleep(self.throttle)
        return squads
