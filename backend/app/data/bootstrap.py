"""Carga inicial automática de datos cuando faltan predicciones/simulación.

Pensado para ejecutarse al arrancar el contenedor (lo lanza `start.sh` en segundo
plano). Es **idempotente**: si ya hay una simulación calculada, no hace nada. Si
falta (base vacía, o solo se cargaron equipos/partidos a mano), ingiere los datos
oficiales, entrena el modelo, genera predicciones, simula el torneo y sincroniza
las plantillas. Así se auto-repara aunque antes se hubiera corrido solo `sync`.

    python -m app.data.bootstrap            # solo si falta la simulación
    python -m app.data.bootstrap --force    # fuerza la carga/recalculo ahora
"""

from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.simulation import SimulationRun
from app.services.recompute import recompute_pipeline
from app.services.squad_service import build_player_providers, sync_squads

logger = logging.getLogger("maya.bootstrap")


async def _needs_bootstrap() -> bool:
    """Falta la carga si todavía no existe ninguna simulación (último artefacto)."""
    async with AsyncSessionLocal() as db:
        sim = (await db.execute(select(SimulationRun.id).limit(1))).first()
    return sim is None


async def run(force: bool = False) -> None:
    if not force and not settings.enable_bootstrap:
        return
    if not force and not await _needs_bootstrap():
        logger.info("Predicciones/simulación ya presentes; no se ejecuta la carga inicial.")
        print("[bootstrap] datos ya cargados; nada que hacer.", flush=True)
        return

    print("[bootstrap] faltan predicciones/simulación: cargando/recalculando…", flush=True)
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
    asyncio.run(run(force="--force" in sys.argv))
