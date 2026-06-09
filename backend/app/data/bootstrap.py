"""Carga inicial automática de datos cuando la base está vacía.

Pensado para ejecutarse al arrancar el contenedor (lo lanza `start.sh` en segundo
plano). Es **idempotente**: si ya hay equipos cargados, no hace nada. Si la base
está vacía, ingiere los datos oficiales, entrena el modelo, genera predicciones,
simula el torneo y sincroniza las plantillas.

    python -m app.data.bootstrap
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.team import Team
from app.services.recompute import recompute_pipeline
from app.services.squad_service import build_player_providers, sync_squads

logger = logging.getLogger("maya.bootstrap")


async def _already_loaded() -> bool:
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(Team))).scalar_one()
    return count > 0


async def run() -> None:
    if not settings.enable_bootstrap:
        return
    if await _already_loaded():
        logger.info("Datos ya cargados; no se ejecuta la carga inicial.")
        print("[bootstrap] datos ya cargados; nada que hacer.", flush=True)
        return

    print("[bootstrap] base vacía: cargando datos iniciales…", flush=True)
    try:
        # Partidos oficiales + entrenamiento + predicciones + simulación.
        async with AsyncSessionLocal() as db:
            summary = await recompute_pipeline(db, trigger="bootstrap", force=True)
            await db.commit()
        print(f"[bootstrap] datos del torneo y modelo listos: {summary}", flush=True)

        # Plantillas (según PLAYER_SOURCES; sin claves usa el fixture de muestra).
        providers = build_player_providers()
        if providers:
            async with AsyncSessionLocal() as db:
                run_ = await sync_squads(db, providers, trigger="bootstrap")
                await db.commit()
            print(f"[bootstrap] plantillas: {run_.message}", flush=True)

        print("[bootstrap] completado.", flush=True)
    except Exception as exc:  # noqa: BLE001
        # No es fatal: el scheduler reintentará en el próximo ciclo.
        logger.exception("La carga inicial falló.")
        print(f"[bootstrap] AVISO: falló la carga inicial ({exc}). El scheduler lo reintentará.", flush=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
