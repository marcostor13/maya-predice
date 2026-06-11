"""Proveedor de marcador en vivo vía scraping de Google (ULTIMO RECURSO).

ADVERTENCIA: best-effort y FRAGIL. Google ofusca el HTML del widget deportivo,
sirve captchas y cambia el marcado sin aviso. Este proveedor NO debe usarse como
fuente principal: existe solo como último eslabón de la cadena de fallback cuando
ESPN y TheSportsDB no devuelven nada. Si no puede extraer un marcador fiable para
un candidato, lo OMITE (nunca inventa).

A diferencia de las demás fuentes, necesita `candidates`: Google no permite
listar "todos los partidos en juego", así que consulta uno por uno los partidos
que el servicio cree in-play (`{home} {away} en vivo`).

Host a allowlistar en producción: `www.google.com`.
"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx

from app.data.live.base import LiveCandidate, LiveFixture, LiveProvider

logger = logging.getLogger("maya.live")

_MAX_CANDIDATES = 6
_THROTTLE_SECONDS = 0.5
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_FINISHED_TOKENS = ("finalizado", "ft", "final", "terminado")

# Marcador del widget: dos números separados por guion/dos puntos (p. ej. "2 - 1").
_SCORE_RE = re.compile(r"(\d{1,2})\s*[-:–]\s*(\d{1,2})")
# Bloques tipo `>2<` ... `>1<` que Google usa para cada marcador.
_TAG_NUM_RE = re.compile(r">(\d{1,2})<")


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def _parse_score(html: str) -> tuple[int, int] | None:
    """Heurística defensiva: intenta extraer (goles_local, goles_visitante)."""
    if not html:
        return None
    text = _strip_tags(html)
    m = _SCORE_RE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Estrategia secundaria: dos primeros números dentro de tags consecutivos.
    nums = _TAG_NUM_RE.findall(html)
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    return None


def _looks_finished(html: str) -> bool:
    text = _strip_tags(html).lower()
    return any(tok in text for tok in _FINISHED_TOKENS)


class GoogleScrapeLiveProvider(LiveProvider):
    name = "google"

    async def _fetch_one(
        self, client: httpx.AsyncClient, cand: LiveCandidate
    ) -> LiveFixture | None:
        query = f"{cand.home_name} {cand.away_name} en vivo"
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept-Language": "es-ES,es;q=0.9",
        }
        resp = await client.get(
            "https://www.google.com/search",
            params={"q": query, "hl": "es", "gl": "es"},
            headers=headers,
        )
        resp.raise_for_status()
        html = resp.text
        score = _parse_score(html)
        if score is None:
            return None
        finished = _looks_finished(html)
        return LiveFixture(
            home_code=cand.home_code,
            away_code=cand.away_code,
            home_name=cand.home_name,
            away_name=cand.away_name,
            kickoff_date=cand.kickoff_date,
            minute=None,
            status="FT" if finished else "LIVE",
            home_goals=score[0],
            away_goals=score[1],
            finished=finished,
        )

    async def fetch_live(
        self, candidates: list[LiveCandidate] | None = None
    ) -> list[LiveFixture]:
        if not candidates:
            return []

        fixtures: list[LiveFixture] = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for idx, cand in enumerate(candidates[:_MAX_CANDIDATES]):
                if idx:
                    await asyncio.sleep(_THROTTLE_SECONDS)
                try:
                    fx = await self._fetch_one(client, cand)
                except Exception as exc:  # noqa: BLE001 — captcha/timeout no rompe nada
                    logger.warning(
                        "Scraping de Google falló para %s-%s: %s",
                        cand.home_name,
                        cand.away_name,
                        exc,
                    )
                    continue
                if fx is not None:
                    fixtures.append(fx)
        return fixtures
