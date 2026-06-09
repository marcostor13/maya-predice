"""Proveedor openfootball: datos del Mundial 2026 en dominio público.

Fuente: https://github.com/openfootball/worldcup.json (JSON derivado del
calendario oficial de la FIFA, sin API key). Es la fuente primaria por ser
accesible desde servidores y libre; la API propia de la FIFA (api.fifa.com)
bloquea clientes de servidor (403). Ver ADR-004 en ARCHITECTURE.md.

El parseo (`parse_matches`) es una función pura sobre el dict JSON, de modo que
puede testearse sin acceso a red.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import settings
from app.data.providers.base import DataProvider, ProviderMatch
from app.data.team_mapping import resolve_team
from app.models.match import MatchStage

_ROUND_TO_STAGE: dict[str, MatchStage] = {
    "Round of 32": MatchStage.ROUND_OF_32,
    "Round of 16": MatchStage.ROUND_OF_16,
    "Quarter-final": MatchStage.QUARTER,
    "Semi-final": MatchStage.SEMI,
    "Match for third place": MatchStage.THIRD_PLACE,
    "Final": MatchStage.FINAL,
}

_MATCHDAY_RE = re.compile(r"Matchday\s+(\d+)")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*UTC([+-]\d{1,2})$")


def _parse_kickoff(date_str: str, time_str: str | None) -> datetime | None:
    """Convierte fecha + 'HH:MM UTC-6' a datetime en UTC."""
    if not date_str:
        return None
    if not time_str:
        return datetime.fromisoformat(date_str).replace(tzinfo=UTC)
    m = _TIME_RE.match(time_str.strip())
    if not m:
        return datetime.fromisoformat(date_str).replace(tzinfo=UTC)
    hour, minute, offset = int(m.group(1)), int(m.group(2)), int(m.group(3))
    local = datetime.fromisoformat(date_str).replace(hour=hour, minute=minute)
    # hora local = UTC + offset  =>  UTC = local - offset
    return (local - timedelta(hours=offset)).replace(tzinfo=UTC)


def _normalize_group(group: str | None) -> str | None:
    """'Group A' -> 'A'. Devuelve None si no hay grupo (eliminatorias)."""
    if not group:
        return None
    return group.replace("Group", "").strip() or None


def _stage_and_matchday(round_str: str, group: str | None) -> tuple[MatchStage, int | None]:
    if round_str in _ROUND_TO_STAGE:
        return _ROUND_TO_STAGE[round_str], None
    md = _MATCHDAY_RE.search(round_str or "")
    matchday = int(md.group(1)) if md else None
    return MatchStage.GROUP, matchday


def _external_ref(
    stage: MatchStage,
    group: str | None,
    home_token: str,
    away_token: str,
    date_str: str,
    time_str: str | None,
    venue: str | None,
) -> str:
    """Clave estable para upsert.

    - Fase de grupos: las selecciones están definidas -> clave por grupo+equipos.
    - Eliminatorias: los participantes cambian (placeholders que se resuelven) ->
      clave por la "ranura" (fase + fecha + hora + sede), que no cambia.
    """
    if stage == MatchStage.GROUP:
        return f"G:{group}:{home_token}-{away_token}"
    return f"K:{stage.value}:{date_str}:{time_str or ''}:{venue or ''}"


def parse_matches(data: dict) -> list[ProviderMatch]:
    """Parsea el JSON de openfootball a una lista de ProviderMatch (función pura)."""
    result: list[ProviderMatch] = []
    for raw in data.get("matches", []):
        group = _normalize_group(raw.get("group"))
        stage, matchday = _stage_and_matchday(raw.get("round", ""), group)

        home_raw, away_raw = raw.get("team1"), raw.get("team2")
        home = resolve_team(home_raw) if home_raw else None
        away = resolve_team(away_raw) if away_raw else None

        date_str = raw.get("date", "")
        time_str = raw.get("time")
        venue = raw.get("ground")

        home_token = home[1] if home else (home_raw or "?")
        away_token = away[1] if away else (away_raw or "?")

        score = raw.get("score") or {}
        ft = score.get("ft") if isinstance(score, dict) else None
        home_goals = away_goals = None
        if isinstance(ft, list) and len(ft) == 2:
            home_goals, away_goals = int(ft[0]), int(ft[1])

        result.append(
            ProviderMatch(
                external_ref=_external_ref(
                    stage, group, home_token, away_token, date_str, time_str, venue
                ),
                stage=stage,
                matchday=matchday,
                group=group,
                home_name=home[0] if home else None,
                away_name=away[0] if away else None,
                home_code=home[1] if home else None,
                away_code=away[1] if away else None,
                home_confederation=home[2] if home else None,
                away_confederation=away[2] if away else None,
                home_placeholder=None if home else home_raw,
                away_placeholder=None if away else away_raw,
                kickoff=_parse_kickoff(date_str, time_str),
                venue=venue,
                home_goals=home_goals,
                away_goals=away_goals,
            )
        )
    return result


class OpenFootballProvider(DataProvider):
    name = "openfootball"

    def __init__(self, url: str | None = None):
        self.url = url or settings.data_source_url

    async def fetch_matches(self) -> list[ProviderMatch]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
            return parse_matches(resp.json())
