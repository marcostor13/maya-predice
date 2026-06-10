"""Lanzador de trabajos en segundo plano para el panel admin.

Ejecuta **un** job pesado a la vez (p. ej. el recompute) sin bloquear la petición
HTTP. El estado se persiste en `job_runs` para que, con varios workers Gunicorn,
el polling del panel lo vea desde cualquier worker. La tarea corre con su **propia
sesión de DB** porque la de la petición se cierra al responder.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.job import JobRun

logger = logging.getLogger("maya.jobs")

# Un job en 'running' más viejo que esto se considera muerto (worker reiniciado):
# no bloquea lanzar uno nuevo. El recompute real tarda < 3 min.
STALE_AFTER = timedelta(minutes=30)

Work = Callable[[AsyncSession], Awaitable[dict]]

# Mantiene referencias a las tareas en vuelo para que el GC no las cancele.
_tasks: set[asyncio.Task] = set()


class JobInProgress(Exception):
    """Ya hay un trabajo activo; no se lanza otro."""

    def __init__(self, job: JobRun) -> None:
        self.job = job
        super().__init__(f"Ya hay un trabajo en curso: {job.name}")


def _aware(dt: datetime | None) -> datetime | None:
    """Normaliza a UTC con tzinfo (Postgres puede devolver naive según el driver)."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def job_to_dict(job: JobRun | None) -> dict:
    if job is None:
        return {"status": "idle"}
    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "running": job.status == "running",
        "result": job.result,
        "error": job.error,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


async def latest_job(db: AsyncSession, name: str | None = None) -> JobRun | None:
    stmt = select(JobRun).order_by(JobRun.id.desc()).limit(1)
    if name:
        stmt = select(JobRun).where(JobRun.name == name).order_by(JobRun.id.desc()).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def _active_job(db: AsyncSession) -> JobRun | None:
    """Devuelve el job realmente activo; marca como error los obsoletos (worker caído)."""
    rows = (await db.execute(select(JobRun).where(JobRun.status == "running"))).scalars().all()
    cutoff = datetime.now(UTC) - STALE_AFTER
    active: JobRun | None = None
    for r in rows:
        if (_aware(r.started_at) or cutoff) < cutoff:
            r.status = "error"
            r.error = "El trabajo no terminó (worker reiniciado)."
            r.finished_at = datetime.now(UTC)
        else:
            active = r
    return active


def _spawn(coro: Awaitable[None]) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def start_job(db: AsyncSession, name: str, work: Work, *, trigger: str = "admin") -> JobRun:
    """Crea el `JobRun` y lanza la tarea en segundo plano. Lanza `JobInProgress` si ya hay uno."""
    active = await _active_job(db)
    if active is not None:
        raise JobInProgress(active)
    job = JobRun(name=name, status="running", trigger=trigger)
    db.add(job)
    await db.flush()
    job_id = job.id
    await db.commit()
    _spawn(_run(job_id, name, work))
    return job


async def _run(job_id: int, name: str, work: Work) -> None:
    """Ejecuta el trabajo con sesión propia y registra el resultado o el fallo."""
    try:
        async with AsyncSessionLocal() as session:
            result = await work(session)
            job = await session.get(JobRun, job_id)
            if job is not None:
                job.status = "done"
                job.result = result
                job.finished_at = datetime.now(UTC)
            await session.commit()
        logger.info("Job '%s' (#%s) completado.", name, job_id)
    except Exception as exc:  # noqa: BLE001 — cualquier fallo se registra en el job
        logger.exception("Job '%s' (#%s) falló.", name, job_id)
        await _mark_error(job_id, str(exc))


async def _mark_error(job_id: int, message: str) -> None:
    try:
        async with AsyncSessionLocal() as session:
            job = await session.get(JobRun, job_id)
            if job is not None:
                job.status = "error"
                job.error = message[:1000]
                job.finished_at = datetime.now(UTC)
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo registrar el fallo del job #%s.", job_id)
