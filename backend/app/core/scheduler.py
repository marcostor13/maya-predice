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
from app.services.app_settings import apply_overrides
from app.services.jobs import JobInProgress, start_job
from app.services.notifications import notify_subscribers
from app.services.recompute import recompute_pipeline
from app.services.squad_service import build_player_providers, sync_squads

logger = logging.getLogger("maya.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def _refresh_overrides() -> None:
    """Recarga los overrides de configuración (panel admin) antes de cada job, para
    que los 2 workers converjan al último valor guardado."""
    async with AsyncSessionLocal() as db:
        try:
            await apply_overrides(db)
        except Exception:  # noqa: BLE001
            logger.warning("No se pudieron recargar los overrides de configuración.")


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


async def _trigger_recompute(trigger: str, *, force: bool) -> bool:
    """Lanza el recálculo **serializado** (un job a la vez, vía `start_job`).

    Devuelve True si lo lanzó; False si ya había uno en curso (otro worker/cron o un
    recálculo manual del admin). El recálculo corre en segundo plano con su propia
    sesión y queda registrado en `job_runs` (visible en el panel).
    """
    async with AsyncSessionLocal() as db:
        try:
            await start_job(
                db, "recompute", lambda s: recompute_pipeline(s, trigger=trigger, force=force)
            )
            return True
        except JobInProgress:
            logger.info("Recálculo (%s) omitido: ya hay uno en curso.", trigger)
            return False
        except Exception:
            await db.rollback()
            logger.exception("No se pudo lanzar el recálculo (%s).", trigger)
            return False


async def run_hourly_refresh() -> None:
    """Aprendizaje continuo (cada hora): recopila de todas las fuentes y reentrena.

    1) sincroniza plantillas multi-fuente (jugadores/lesiones/fotos + DT),
    2) lanza el recálculo forzado (reingesta de resultados + cuotas → reentreno →
       predicciones → simulación). Así el modelo se afina con datos frescos cada hora.
    """
    await _refresh_overrides()
    if not settings.hourly_refresh_enabled:
        return
    logger.info("Aprendizaje continuo (horario)…")
    await _sync_squads_job()
    await _trigger_recompute("hourly", force=True)


async def run_daily_refresh() -> None:
    """Refresco diario: plantillas + recálculo + **digest por email** a suscriptores."""
    logger.info("Refresco diario…")
    await _sync_squads_job()
    await _trigger_recompute("daily", force=True)
    async with AsyncSessionLocal() as db:
        try:
            sent = await notify_subscribers(db, only_with_results=True)
            await db.commit()
            if sent:
                logger.info("Digest enviado a %s suscriptores.", sent)
        except Exception:
            await db.rollback()
            logger.exception("El envío del digest falló.")


async def run_live_update() -> None:
    """Recálculo en vivo: solo trabaja si terminaron/cambiaron partidos (force=False)."""
    await _refresh_overrides()
    if not settings.enable_live_updates:
        return
    await _trigger_recompute("live", force=False)


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
        max_instances=1,
    )
    if settings.hourly_refresh_enabled:
        _scheduler.add_job(
            run_hourly_refresh,
            IntervalTrigger(minutes=settings.hourly_refresh_minutes),
            id="hourly_refresh",
            replace_existing=True,
            max_instances=1,
        )
    if settings.enable_live_updates:
        _scheduler.add_job(
            run_live_update,
            IntervalTrigger(minutes=settings.live_poll_minutes),
            id="live_update",
            replace_existing=True,
            max_instances=1,
        )
    _scheduler.start()
    logger.info(
        "Scheduler activo: diario %02d:%02d UTC; aprendizaje horario cada %s min (%s); "
        "en vivo cada %s min (%s).",
        settings.sync_hour_utc,
        settings.sync_minute_utc,
        settings.hourly_refresh_minutes,
        "on" if settings.hourly_refresh_enabled else "off",
        settings.live_poll_minutes,
        "on" if settings.enable_live_updates else "off",
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def reschedule_scheduler() -> None:
    """Reconstruye el scheduler con la config actual (tras cambiar ajustes en el admin).

    Afecta al worker que atiende la petición; los demás workers recogen los cambios
    de comportamiento (flags) al inicio de su próximo job (recargan overrides)."""
    if not settings.enable_scheduler:
        return
    shutdown_scheduler()
    start_scheduler()
