"""Recálculo en vivo desde la CLI (para cron durante el torneo).

    python -m app.data.recompute

Reingiere resultados y, si terminó algún partido, reentrena el modelo y regenera
las predicciones y la simulación de los partidos venideros.
"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.recompute import recompute_pipeline


async def main() -> None:
    async with AsyncSessionLocal() as db:
        summary = await recompute_pipeline(db, trigger="manual")
        await db.commit()
        print(f"[recompute] {summary}")


if __name__ == "__main__":
    asyncio.run(main())
