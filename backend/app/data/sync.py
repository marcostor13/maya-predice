"""Ejecuta una sincronización con la fuente oficial desde la línea de comandos.

Pensado para cron (p.ej. en Coolify) además del scheduler interno:
    python -m app.data.sync
"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.sync_service import default_provider, sync_official_data


async def main() -> None:
    async with AsyncSessionLocal() as db:
        run = await sync_official_data(db, default_provider(), trigger="manual")
        await db.commit()
        print(
            f"[sync] fuente={run.source} estado={run.status.value} "
            f"vistos={run.matches_seen} altas={run.created} "
            f"actualizados={run.updated} cambios={run.changes_count}"
        )
        if run.message:
            print(f"[sync] {run.message}")


if __name__ == "__main__":
    asyncio.run(main())
