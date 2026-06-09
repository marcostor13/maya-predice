"""Proveedor de fixture local (desarrollo / offline / pruebas).

Lee plantillas desde un JSON (archivo local o URL en la allowlist). Útil cuando
las APIs externas no están disponibles y como tercera fuente curada. El parseo
(`parse_squads`) es puro y testeable.

Esquema del JSON:
{
  "source": "fixture",
  "squads": [
    {"team_code": "ARG",
     "coach": {"name": "...", "nationality": "..."},
     "players": [
        {"full_name": "...", "position": "FWD", "shirt_number": 10,
         "club": "...", "role": "starter", "status": "available"}
     ]}
  ]
}
"""

from __future__ import annotations

import json
from pathlib import Path

from app.data.players._http import get_json
from app.data.players.base import (
    CoachObservation,
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
    normalize_position,
    normalize_role,
    normalize_status,
)


def parse_squads(data: dict, source: str | None = None) -> list[SquadObservation]:
    src = source or data.get("source", "fixture")
    squads: list[SquadObservation] = []
    for s in data.get("squads", []):
        coach = None
        if s.get("coach"):
            coach = CoachObservation(
                source=src,
                name=s["coach"]["name"],
                nationality=s["coach"].get("nationality"),
                status=normalize_status(s["coach"].get("status", "available")),
            )
        players = [
            PlayerObservation(
                source=src,
                full_name=p["full_name"],
                position=normalize_position(p.get("position")),
                shirt_number=p.get("shirt_number"),
                club=p.get("club"),
                role=normalize_role(p.get("role")),
                status=normalize_status(p.get("status")),
            )
            for p in s.get("players", [])
        ]
        squads.append(
            SquadObservation(source=src, team_code=s["team_code"], coach=coach, players=players)
        )
    return squads


class LocalFixtureProvider(PlayerDataProvider):
    name = "fixture"

    def __init__(self, path: str, source: str | None = None):
        self.path = path
        if source:
            self.name = source

    async def fetch_all(self) -> list[SquadObservation]:
        data = json.loads(Path(self.path).read_text(encoding="utf-8"))
        return parse_squads(data, self.name)


class RemoteSquadProvider(PlayerDataProvider):
    """Lee el mismo esquema desde una URL (debe estar en la allowlist)."""

    name = "remote"

    def __init__(self, url: str, source: str | None = None):
        self.url = url
        if source:
            self.name = source

    async def fetch_all(self) -> list[SquadObservation]:
        data = await get_json(self.url)
        return parse_squads(data, self.name)
