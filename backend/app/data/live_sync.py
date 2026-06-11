"""Ingesta del marcador en vivo desde la CLI (para cron externo, p. ej. Coolify).

    python -m app.data.live_sync

Hace un único ciclo ligero: consulta el proveedor live (API-Football) los
partidos en juego y refresca el marcador (goles/minuto/estado) de los `Match`
que casan. No reentrena ni recalcula predicciones. Equivale al job `live_scores`
del scheduler interno, pensado para programarlo con cron cuando
`ENABLE_SCHEDULER=false`. No-op si está desactivado o sin key.
"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.live_scores import sync_live_scores


async def main() -> None:
    async with AsyncSessionLocal() as db:
        summary = await sync_live_scores(db)
        print(f"[live_sync] {summary}")


if __name__ == "__main__":
    asyncio.run(main())
