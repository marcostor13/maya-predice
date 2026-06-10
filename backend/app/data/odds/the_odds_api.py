"""Proveedor de cuotas de mercado vía **The Odds API** (the-odds-api.com).

Las cuotas de cierre son la señal más predictiva que existe (núcleo del método de
Opta). Este proveedor:
1. pide en **una sola llamada** las cuotas 1X2 (mercado ``h2h``) de todos los
   partidos del Mundial (capa gratuita: 500 créditos/mes; con caché basta de sobra),
2. convierte las cuotas decimales en **probabilidad implícita** quitando el margen
   de la casa (overround),
3. promedia las casas y devuelve una terna ``(p_home, p_draw, p_away)`` por partido,
   indexada por los nombres de los equipos normalizados.

La conversión y el parseo son **puros y testeables**; la llamada usa la caché en DB
(`api_cache`) para no gastar créditos repetidos. La clave va en `params` (no en la
clave de caché). Requiere `api.the-odds-api.com` en la allowlist (en el sandbox de
desarrollo no responde).
"""

from __future__ import annotations

from app.data.players._cache import cached_get_json
from app.data.players.base import normalize_name

Triple = tuple[float, float, float]


def decimal_to_probabilities(home: float, draw: float, away: float) -> Triple | None:
    """Cuotas decimales → probabilidad 1X2 sin margen (normalizada a suma 1)."""
    if not (home and draw and away) or min(home, draw, away) <= 0:
        return None
    inv = [1.0 / home, 1.0 / draw, 1.0 / away]
    total = sum(inv)
    if total <= 0:
        return None
    return (inv[0] / total, inv[1] / total, inv[2] / total)


def parse_odds_events(events: list[dict]) -> dict[tuple[str, str], Triple]:
    """Convierte la respuesta de The Odds API en {(local_norm, visitante_norm): terna}.

    Promedia la probabilidad implícita de todas las casas que ofrecen el mercado
    ``h2h`` (1X2). Los `outcomes` nombran al local, al visitante y "Draw".
    """
    out: dict[tuple[str, str], Triple] = {}
    for event in events or []:
        home = event.get("home_team")
        away = event.get("away_team")
        if not home or not away:
            continue
        ternas: list[Triple] = []
        for book in event.get("bookmakers") or []:
            for market in book.get("markets") or []:
                if market.get("key") != "h2h":
                    continue
                prices = {o.get("name"): o.get("price") for o in market.get("outcomes") or []}
                terna = decimal_to_probabilities(
                    prices.get(home), prices.get("Draw"), prices.get(away)
                )
                if terna:
                    ternas.append(terna)
        if ternas:
            n = len(ternas)
            avg = (
                sum(t[0] for t in ternas) / n,
                sum(t[1] for t in ternas) / n,
                sum(t[2] for t in ternas) / n,
            )
            out[(normalize_name(home), normalize_name(away))] = avg
    return out


class TheOddsApiProvider:
    name = "the_odds_api"

    def __init__(
        self,
        api_key: str,
        base: str,
        sport_key: str,
        regions: str = "eu",
        ttl_hours: int = 6,
    ):
        self.api_key = api_key
        self.base = base.rstrip("/")
        self.sport_key = sport_key
        self.regions = regions
        self.ttl_hours = ttl_hours

    async def fetch_match_probabilities(self) -> dict[tuple[str, str], Triple]:
        """Devuelve {(local_norm, visitante_norm): (p_h, p_d, p_a)} de todos los partidos."""
        url = f"{self.base}/sports/{self.sport_key}/odds"
        data = await cached_get_json(
            url,
            cache_key=f"theoddsapi:{self.sport_key}:{self.regions}:h2h",
            source="the_odds_api",
            params={
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": "h2h",
                "oddsFormat": "decimal",
            },
            ttl_hours=self.ttl_hours,
        )
        return parse_odds_events(data if isinstance(data, list) else [])
