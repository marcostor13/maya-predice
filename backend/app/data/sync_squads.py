"""Sincroniza las plantillas (multi-fuente, por consenso) desde la CLI.

    python -m app.data.sync_squads

Las fuentes activas se controlan con PLAYER_SOURCES (.env). Por defecto usa el
fixture local; en producción se activan apifootball, thesportsdb y wikidata.
"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.squad_service import build_player_providers, sync_squads


async def main() -> None:
    providers = build_player_providers()
    if not providers:
        print("[squads] No hay fuentes configuradas (PLAYER_SOURCES vacío).")
        return
    async with AsyncSessionLocal() as db:
        run = await sync_squads(db, providers, trigger="manual")
        await db.commit()
        print(f"[squads] fuentes={[p.name for p in providers]} estado={run.status.value}")
        print(f"[squads] {run.message}")


if __name__ == "__main__":
    asyncio.run(main())
