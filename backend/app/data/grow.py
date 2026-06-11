"""Agente de crecimiento desde la CLI (para cron externo, p. ej. en Coolify).

    python -m app.data.grow

Ejecuta un ciclo del agente: genera ideas de promoción/SEO/contenido/monetización
con DeepSeek, ejecuta acciones automáticas seguras (ping a IndexNow) y envía el
digest al dueño. Equivale al job del scheduler interno, pensado para programarlo
con el cron de Coolify cuando `ENABLE_SCHEDULER=false`. Corre síncrono (un proceso
que termina al acabar). No hace nada si falta DEEPSEEK_API_KEY (avisa por email).
"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.growth.agent import run_growth_cycle


async def main() -> None:
    async with AsyncSessionLocal() as db:
        summary = await run_growth_cycle(db, trigger="cron")
        print(f"[grow] ciclo de crecimiento: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
