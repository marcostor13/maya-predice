"""Programador de jobs (APScheduler).

Dos jobs:
- **Diario** (SYNC_HOUR_UTC): refresco completo — sincroniza plantillas
  multi-fuente y ejecuta el pipeline de recálculo (resultados → modelo →
  predicciones → simulación).
- **En vivo** (cada LIVE_POLL_MINUTES, si ENABLE_LIVE_UPDATES): durante el torneo
  reingiere resultados y, si terminó algún partido, recalcula la cadena. Así, a
  medida que acaban los partidos, las predicciones y la simulación se actualizan.

En entornos con cron externo (Coolify) se puede desactivar el scheduler
(ENABLE_SCHEDULER=false) y programar `python -m app.data.recompute` y
`python -m app.data.sync_squads`.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.recompute import recompute_pipeline
from app.services.squad_service import build_player_providers, sync_squads

logger = logging.getLogger("maya.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def _sync_squads_job() -> None:
    providers = build_player_providers()
    if not providers:
        return
    async with AsyncSessionLocal() as db:
        try:
            run = await sync_squads(db, providers, trigger="scheduled")
            await db.commit()
            logger.info("Plantillas: %s", run.message)
        except Exception:
            await db.rollback()
            logger.exception("La verificación de plantillas falló.")


async def run_daily_refresh() -> None:
    """Refresco diario completo: plantillas + recálculo forzado (modelo/pred/sim)."""
    logger.info("Refresco diario…")
    await _sync_squads_job()
    async with AsyncSessionLocal() as db:
        try:
            summary = await recompute_pipeline(db, trigger="scheduled", force=True)
            await db.commit()
            logger.info("Refresco diario completo: %s", summary)
        except Exception:
            await db.rollback()
            logger.exception("El refresco diario falló.")


async def run_live_update() -> None:
    """Recálculo en vivo: solo trabaja si terminaron/ cambiaron partidos."""
    async with AsyncSessionLocal() as db:
        try:
            summary = await recompute_pipeline(db, trigger="live")
            await db.commit()
            if summary["recomputed"]:
                logger.info("Actualización en vivo aplicada: %s", summary)
        except Exception:
            await db.rollback()
            logger.exception("La actualización en vivo falló.")


def start_scheduler() -> None:
    global _scheduler
    if not settings.enable_scheduler or _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_daily_refresh,
        CronTrigger(hour=settings.sync_hour_utc, minute=settings.sync_minute_utc),
        id="daily_refresh",
        replace_existing=True,
    )
    if settings.enable_live_updates:
        _scheduler.add_job(
            run_live_update,
            IntervalTrigger(minutes=settings.live_poll_minutes),
            id="live_update",
            replace_existing=True,
        )
    _scheduler.start()
    logger.info(
        "Scheduler activo: refresco diario %02d:%02d UTC; en vivo cada %s min (%s).",
        settings.sync_hour_utc,
        settings.sync_minute_utc,
        settings.live_poll_minutes,
        "on" if settings.enable_live_updates else "off",
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
