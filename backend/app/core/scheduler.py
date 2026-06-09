"""Programador del job diario de verificación de datos oficiales.

Usa APScheduler (AsyncIOScheduler) para ejecutar la sincronización una vez al
día a la hora configurada (SYNC_HOUR_UTC), tras finalizar los partidos de la
jornada. Para entornos donde se prefiera cron externo (Coolify), basta con
desactivar el scheduler (ENABLE_SCHEDULER=false) y programar `python -m
app.data.sync`.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.prediction.training import persist_team_strengths, train_model
from app.services.squad_service import build_player_providers, sync_squads
from app.services.sync_service import default_provider, sync_official_data

logger = logging.getLogger("maya.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def run_daily_sync() -> None:
    """Job diario: verifica datos oficiales (partidos) y plantillas multi-fuente."""
    logger.info("Iniciando verificación diaria…")
    async with AsyncSessionLocal() as db:
        try:
            run = await sync_official_data(db, default_provider(), trigger="scheduled")
            await db.commit()
            logger.info(
                "Partidos: %s altas, %s actualizados, %s cambios.",
                run.created,
                run.updated,
                run.changes_count,
            )
        except Exception:
            await db.rollback()
            logger.exception("La verificación de partidos falló.")

    providers = build_player_providers()
    if providers:
        async with AsyncSessionLocal() as db:
            try:
                run = await sync_squads(db, providers, trigger="scheduled")
                await db.commit()
                logger.info("Plantillas: %s", run.message)
            except Exception:
                await db.rollback()
                logger.exception("La verificación de plantillas falló.")

    # Reentrena el modelo con los resultados actualizados y persiste las fuerzas.
    async with AsyncSessionLocal() as db:
        try:
            model = await train_model(db, force=True)
            await persist_team_strengths(db, model)
            await db.commit()
            logger.info("Modelo reentrenado: %s equipos.", len(model.teams))
        except Exception:
            await db.rollback()
            logger.exception("El reentrenamiento del modelo falló.")


def start_scheduler() -> None:
    global _scheduler
    if not settings.enable_scheduler or _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_daily_sync,
        CronTrigger(hour=settings.sync_hour_utc, minute=settings.sync_minute_utc),
        id="daily_official_sync",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler activo: verificación diaria a las %02d:%02d UTC.",
        settings.sync_hour_utc,
        settings.sync_minute_utc,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
