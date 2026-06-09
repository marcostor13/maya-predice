"""Proveedor Wikidata (fuente 3 de 3).

Fuente abierta sin API key. Resuelve la entidad de la selección nacional y
consulta su plantilla vía SPARQL (P54 «miembro de equipo deportivo», P413
«posición de juego»). Requiere que `query.wikidata.org` y `www.wikidata.org`
estén en la allowlist del entorno. Es la fuente más ruidosa (Wikidata no siempre
mantiene la convocatoria vigente), por eso pesa menos en los desempates de
consenso. Ver DEVLOG.md.
"""

from __future__ import annotations

from app.data.players._http import get_json
from app.data.players.base import (
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
    normalize_position,
)
from app.data.team_mapping import TEAMS

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SEARCH_ENDPOINT = "https://www.wikidata.org/w/api.php"

_SQUAD_QUERY = """
SELECT ?playerLabel ?positionLabel WHERE {{
  ?statement ps:P54 wd:{team_qid} .
  ?player p:P54 ?statement .
  OPTIONAL {{ ?player wdt:P413 ?position . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}} LIMIT 60
"""


class WikidataProvider(PlayerDataProvider):
    name = "wikidata"

    async def _team_qid(self, team_name: str) -> str | None:
        data = await get_json(
            SEARCH_ENDPOINT,
            params={
                "action": "wbsearchentities",
                "search": f"{team_name} national football team",
                "language": "en",
                "format": "json",
                "limit": 1,
            },
        )
        results = data.get("search") or []
        return results[0]["id"] if results else None

    async def _squad(self, qid: str) -> list[PlayerObservation]:
        data = await get_json(
            SPARQL_ENDPOINT,
            headers={"Accept": "application/sparql-results+json"},
            params={"query": _SQUAD_QUERY.format(team_qid=qid), "format": "json"},
        )
        out: list[PlayerObservation] = []
        for row in data.get("results", {}).get("bindings", []):
            name = row.get("playerLabel", {}).get("value")
            if not name or name.startswith("Q"):  # etiqueta no resuelta
                continue
            out.append(
                PlayerObservation(
                    source=self.name,
                    full_name=name,
                    position=normalize_position(row.get("positionLabel", {}).get("value")),
                )
            )
        return out

    async def fetch_all(self) -> list[SquadObservation]:
        squads: list[SquadObservation] = []
        for team_name, (code, _conf) in TEAMS.items():
            try:
                qid = await self._team_qid(team_name)
                if not qid:
                    continue
                players = await self._squad(qid)
            except RuntimeError:
                continue
            if players:
                squads.append(
                    SquadObservation(source=self.name, team_code=code, coach=None, players=players)
                )
        return squads
