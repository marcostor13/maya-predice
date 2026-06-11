"""Ingesta ligera de marcadores en vivo (in-play).

Cada ~2 min consulta al proveedor live (API-Football) los partidos en juego y
actualiza el marcador de los `Match` que casan por (códigos de equipo + fecha de
kickoff). Es **ligero a propósito**: no reentrena ni recalcula predicciones — de
eso siguen encargándose los jobs existentes cuando un partido termina.

No-op si la función está desactivada o sin key (no toca la red).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.live.apifootball import APIFootballLiveProvider
from app.data.live.base import LiveCandidate, LiveFixture, LiveProvider
from app.data.live.espn import ESPNLiveProvider
from app.data.live.google import GoogleScrapeLiveProvider
from app.data.live.thesportsdb import TheSportsDBLiveProvider
from app.models.match import Match, MatchStatus
from app.models.team import Team
from app.services.app_settings import apply_overrides

logger = logging.getLogger("maya.live")

# Margen para casar fixtures por fecha de kickoff (zonas horarias / datos imprecisos).
_DATE_TOLERANCE_DAYS = 1
# Un partido LIVE que ya no aparece en el feed y cuyo kickoff fue hace más de esto
# se marca FINISHED por seguridad (un partido dura ~120 min como mucho).
_STALE_LIVE_MINUTES = 150
# Ventana en la que un partido se considera "probablemente in-play" (para Google).
_INPLAY_WINDOW_MINUTES = 150


def _build_providers() -> list[LiveProvider]:
    """Construye la cadena de proveedores live según `live_source` (orden = prioridad)."""
    providers: list[LiveProvider] = []
    for raw in settings.live_source.split(","):
        token = raw.strip().lower()
        if not token:
            continue
        if token == "espn":
            providers.append(ESPNLiveProvider())
        elif token == "thesportsdb":
            providers.append(TheSportsDBLiveProvider(settings.thesportsdb_key))
        elif token == "google":
            providers.append(GoogleScrapeLiveProvider())
        elif token == "apifootball" and settings.apifootball_key:
            providers.append(
                APIFootballLiveProvider(
                    settings.apifootball_key, settings.apifootball_host
                )
            )
        # tokens desconocidos: se ignoran
    return providers


def _kickoff_date(match: Match) -> date | None:
    if match.kickoff is None:
        return None
    return match.kickoff.astimezone(UTC).date()


def _dates_match(a: date | None, b: date | None) -> bool:
    if a is None or b is None:
        return True  # sin fecha fiable, no descartamos por fecha
    return abs((a - b).days) <= _DATE_TOLERANCE_DAYS


async def sync_live_scores(db: AsyncSession) -> dict:
    """Ingiere los marcadores en vivo y actualiza los partidos. Devuelve un resumen."""
    await apply_overrides(db)

    if not settings.enable_live_scores:
        return {"updated": 0, "live": 0, "skipped": True}

    providers = _build_providers()
    if not providers:
        return {"updated": 0, "live": 0, "skipped": True}

    now = datetime.now(UTC)
    today = now.date()

    # Candidatos: programados/en vivo o con kickoff dentro de ±1 día.
    window_lo = now - timedelta(days=1)
    window_hi = now + timedelta(days=1)
    stmt = select(Match).where(
        (Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.LIVE]))
        | (Match.kickoff.between(window_lo, window_hi))
    )
    matches = list((await db.execute(stmt)).scalars().all())

    # Resolución id_equipo -> código (una sola consulta de equipos).
    teams = {t.id: t for t in (await db.execute(select(Team))).scalars().all()}

    def _codes(match: Match) -> tuple[str | None, str | None]:
        home = teams.get(match.home_team_id) if match.home_team_id else None
        away = teams.get(match.away_team_id) if match.away_team_id else None
        return (home.code if home else None, away.code if away else None)

    def _names(match: Match) -> tuple[str | None, str | None]:
        home = teams.get(match.home_team_id) if match.home_team_id else None
        away = teams.get(match.away_team_id) if match.away_team_id else None
        return (home.name if home else None, away.name if away else None)

    # Sublista "probablemente in-play" para las fuentes que necesitan candidatos
    # (Google): kickoff pasado hace < 150 min y estado scheduled/live.
    inplay_cutoff = now - timedelta(minutes=_INPLAY_WINDOW_MINUTES)
    candidates: list[LiveCandidate] = []
    for match in matches:
        if match.status not in (MatchStatus.SCHEDULED, MatchStatus.LIVE):
            continue
        if match.kickoff is None:
            continue
        ko = match.kickoff.astimezone(UTC)
        if not (inplay_cutoff <= ko <= now):
            continue
        hc, ac = _codes(match)
        hn, an = _names(match)
        candidates.append(
            LiveCandidate(
                home_code=hc,
                away_code=ac,
                home_name=hn,
                away_name=an,
                kickoff_date=_kickoff_date(match),
            )
        )

    # Cadena de fallback: usa el primer proveedor que devuelva algo.
    fixtures: list[LiveFixture] = []
    source: str | None = None
    for provider in providers:
        try:
            result = await provider.fetch_live(candidates)
        except Exception as exc:  # noqa: BLE001 — una fuente caída no tumba el ciclo
            logger.warning("Fuente live '%s' falló: %s", provider.name, exc)
            continue
        if result:
            fixtures = result
            source = provider.name
            logger.info("Marcador en vivo servido por '%s' (%s fixtures).", source, len(result))
            break

    updated = 0
    live = 0
    finished = 0
    matched_ids: set[int] = set()

    for fx in fixtures:
        if not fx.home_code or not fx.away_code:
            continue
        target: Match | None = None
        for match in matches:
            hc, ac = _codes(match)
            if hc == fx.home_code and ac == fx.away_code and _dates_match(
                _kickoff_date(match), fx.kickoff_date
            ):
                target = match
                break
        if target is None:
            continue

        matched_ids.add(target.id)
        if fx.finished:
            target.status = MatchStatus.FINISHED
            target.minute = None
            finished += 1
        else:
            target.status = MatchStatus.LIVE
            target.minute = fx.minute
            live += 1
        target.home_goals = fx.home_goals
        target.away_goals = fx.away_goals
        target.live_updated_at = now
        updated += 1

    # Defensivo: partidos que estaban LIVE pero ya no llegan en el feed y cuyo
    # kickoff fue hace bastante → ciérralos como FINISHED.
    stale_cutoff = now - timedelta(minutes=_STALE_LIVE_MINUTES)
    for match in matches:
        if (
            match.status == MatchStatus.LIVE
            and match.id not in matched_ids
            and match.kickoff is not None
            and match.kickoff.astimezone(UTC) < stale_cutoff
        ):
            match.status = MatchStatus.FINISHED
            match.minute = None
            match.live_updated_at = now
            finished += 1
            updated += 1

    await db.commit()
    logger.info(
        "Marcadores en vivo (%s): %s actualizados, %s en juego, %s finalizados.",
        today.isoformat(),
        updated,
        live,
        finished,
    )
    return {"updated": updated, "live": live, "finished": finished, "source": source}
