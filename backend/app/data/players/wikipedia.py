"""Proveedor por *web scraping* de Wikipedia (squads, entrenador y fotos).

Usa la **API de MediaWiki** (en.wikipedia.org) — legal y sin clave — para extraer:
- la plantilla de cada selección desde las plantillas wiki ``{{nat fs player}}``
  (dorsal, posición, nombre y club),
- el seleccionador (``| manager = [[…]]`` del infobox),
- y la **foto** de cada jugador/DT vía ``prop=pageimages`` (en lote).

El parseo del wikitexto es **puro y testeable** (`parse_squad_wikitext`). Requiere
que `en.wikipedia.org` esté en la allowlist del entorno (en producción se añade;
en el sandbox de desarrollo NO responde). Defensivo: un equipo que falle se salta.
"""

from __future__ import annotations

import re

from app.data.players._http import get_json
from app.data.players.base import (
    CoachObservation,
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
    normalize_position,
)
from app.data.team_mapping import TEAMS

API = "https://en.wikipedia.org/w/api.php"

# Títulos de Wikipedia que difieren del patrón "<País> national football team".
TITLE_OVERRIDES = {
    "United States": "United States men's national soccer team",
    "USA": "United States men's national soccer team",
}

# {{nat fs player|no=1|pos=GK|name=[[X]]|club=[[Y]]|...}}  (también "nat fs g player")
_PLAYER_TPL = re.compile(r"\{\{\s*nat fs (?:g )?player\b([^}]*)\}\}", re.IGNORECASE)
_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_MANAGER = re.compile(r"\|\s*(?:manager|head[ _]coach|coach)\s*=\s*([^\n|]+)", re.IGNORECASE)


def _param(params: str, key: str) -> str | None:
    # El valor puede contener wikilinks con `|` internos ([[A|B]]); hay que consumir
    # el wikilink completo y solo cortar en el `|` que separa parámetros de plantilla.
    m = re.search(rf"\|\s*{key}\s*=\s*((?:\[\[[^\]]*\]\]|[^|])*)", params)
    return m.group(1).strip() if m else None


def _link(value: str | None) -> tuple[str | None, str | None]:
    """Devuelve (título_de_página, texto_visible) de un wikilink, o (texto, texto)."""
    if not value:
        return (None, None)
    m = _WIKILINK.search(value)
    if m:
        target = m.group(1).strip()
        display = (m.group(2) or m.group(1)).strip()
        return (target, display)
    clean = value.strip()
    return (clean or None, clean or None)


def parse_squad_wikitext(text: str) -> tuple[list[dict], str | None]:
    """Extrae (jugadores, título_del_DT) del wikitexto de la página de la selección.

    Cada jugador: ``{"title","name","no","pos","club"}`` (``title`` = página wiki,
    usada para buscar la foto; ``name`` = texto visible).
    """
    players: list[dict] = []
    for block in _PLAYER_TPL.finditer(text):
        params = block.group(1)
        title, name = _link(_param(params, "name"))
        if not name:
            continue
        club_title, _ = _link(_param(params, "club"))
        number = _param(params, "no")
        players.append(
            {
                "title": title,
                "name": name,
                "no": int(number) if (number or "").isdigit() else None,
                "pos": _param(params, "pos"),
                "club": club_title,
            }
        )
    manager_match = _MANAGER.search(text)
    manager_title = _link(manager_match.group(1))[0] if manager_match else None
    return players, manager_title


class WikipediaSquadProvider(PlayerDataProvider):
    name = "wikipedia"

    def __init__(self, api: str = API):
        self.api = api

    async def _wikitext(self, title: str) -> str | None:
        data = await get_json(
            self.api,
            params={
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": title,
                "redirects": 1,
                "format": "json",
                "formatversion": 2,
            },
        )
        pages = data.get("query", {}).get("pages", [])
        for page in pages:
            revs = page.get("revisions") or []
            if revs:
                return revs[0].get("slots", {}).get("main", {}).get("content")
        return None

    async def _photos(self, titles: list[str]) -> dict[str, str]:
        """Miniatura por título de página (en lotes de 50, el máximo de la API)."""
        out: dict[str, str] = {}
        unique = [t for t in dict.fromkeys(titles) if t]
        for i in range(0, len(unique), 50):
            chunk = unique[i : i + 50]
            data = await get_json(
                self.api,
                params={
                    "action": "query",
                    "prop": "pageimages",
                    "piprop": "thumbnail",
                    "pithumbsize": 200,
                    "titles": "|".join(chunk),
                    "redirects": 1,
                    "format": "json",
                    "formatversion": 2,
                },
            )
            for page in data.get("query", {}).get("pages", []):
                thumb = page.get("thumbnail", {}).get("source")
                if page.get("title") and thumb:
                    out[page["title"]] = thumb
        return out

    async def _squad(self, team_name: str, code: str) -> SquadObservation | None:
        title = TITLE_OVERRIDES.get(team_name, f"{team_name} national football team")
        wikitext = await self._wikitext(title)
        if not wikitext:
            return None
        raw_players, manager_title = parse_squad_wikitext(wikitext)
        if not raw_players:
            return None

        photo_titles = [p["title"] for p in raw_players if p["title"]]
        if manager_title:
            photo_titles.append(manager_title)
        photos = await self._photos(photo_titles)

        players = [
            PlayerObservation(
                source=self.name,
                full_name=p["name"],
                position=normalize_position(p["pos"]),
                shirt_number=p["no"],
                club=p["club"],
                photo_url=photos.get(p["title"]) if p["title"] else None,
            )
            for p in raw_players
        ]
        coach = None
        if manager_title:
            coach = CoachObservation(
                source=self.name, name=manager_title, photo_url=photos.get(manager_title)
            )
        return SquadObservation(source=self.name, team_code=code, coach=coach, players=players)

    async def fetch_all(self) -> list[SquadObservation]:
        squads: list[SquadObservation] = []
        for team_name, (code, _conf) in TEAMS.items():
            try:
                squad = await self._squad(team_name, code)
            except RuntimeError:
                continue  # red caída o página inexistente: salta este equipo
            if squad:
                squads.append(squad)
        return squads
