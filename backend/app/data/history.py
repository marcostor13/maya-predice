"""Ingesta de resultados históricos internacionales para entrenar el modelo.

Fuente: martj42/international_results (dominio público, ~49k partidos desde 1872,
incluye sede neutral). Accesible vía raw.githubusercontent.com. Se mapean los
nombres a los códigos FIFA de las 48 selecciones; el filtro controla qué partidos
se usan para entrenar.

`parse_results` es una función pura sobre el texto CSV (testeable sin red).
"""

from __future__ import annotations

import csv
import io
from datetime import date

import httpx

from app.core.config import settings
from app.data.team_mapping import resolve_history_team
from app.services.prediction.dixon_coles import MatchResult


def _identifier(name: str, team_filter: str) -> str | None:
    """Devuelve el identificador de entrenamiento de un equipo, o None si se filtra."""
    code = resolve_history_team(name)
    if code:
        return code
    # equipo fuera de las 48
    if team_filter == "all" or team_filter == "any":
        return name  # se conserva con su nombre (opponente)
    return None  # team_filter == "both": se descarta


def parse_results(
    csv_text: str, since_year: int = 2018, team_filter: str = "both"
) -> list[MatchResult]:
    """Parsea el CSV de resultados a MatchResult, filtrando por año y equipos.

    team_filter:
      - "both": solo partidos entre dos de las 48 selecciones (rápido y enfocado).
      - "any":  partidos con al menos una de las 48 (más datos, más equipos).
      - "all":  todos los partidos internacionales del periodo.
    """
    out: list[MatchResult] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        date_str = row.get("date", "")
        if not date_str or date_str[:4].isdigit() is False:
            continue
        if int(date_str[:4]) < since_year:
            continue
        hs, as_ = row.get("home_score"), row.get("away_score")
        if hs in (None, "", "NA") or as_ in (None, "", "NA"):
            continue  # partido no jugado (incluye fixtures futuros del propio CSV)

        home = _identifier(row["home_team"], team_filter)
        away = _identifier(row["away_team"], team_filter)
        if home is None or away is None:
            continue
        if team_filter == "any" and not (
            resolve_history_team(row["home_team"]) or resolve_history_team(row["away_team"])
        ):
            continue

        y, m, d = (int(x) for x in date_str.split("-"))
        out.append(
            MatchResult(
                home=home,
                away=away,
                home_goals=int(hs),
                away_goals=int(as_),
                played_on=date(y, m, d),
                neutral=str(row.get("neutral", "")).strip().lower() in ("true", "1", "yes"),
            )
        )
    return out


class ResultsHistoryProvider:
    name = "martj42"

    def __init__(
        self,
        url: str | None = None,
        since_year: int | None = None,
        team_filter: str | None = None,
    ):
        self.url = url or settings.history_source_url
        self.since_year = since_year if since_year is not None else settings.history_since_year
        self.team_filter = team_filter or settings.history_team_filter

    async def fetch_results(self) -> list[MatchResult]:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
            return parse_results(resp.text, self.since_year, self.team_filter)
