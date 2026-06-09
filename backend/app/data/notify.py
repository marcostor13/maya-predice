"""Envía el digest por email a los suscriptores desde la CLI (o cron).

    python -m app.data.notify

Útil para pruebas o para programar el envío por cron. Requiere SMTP configurado
y NOTIFICATIONS_ENABLED=true. Por defecto solo envía si hay resultados nuevos;
usa --force para enviar igualmente.
"""

from __future__ import annotations

import asyncio
import sys

from app.core.database import AsyncSessionLocal
from app.services.notifications import notify_subscribers


async def main() -> None:
    force = "--force" in sys.argv
    async with AsyncSessionLocal() as db:
        sent = await notify_subscribers(db, only_with_results=not force)
        await db.commit()
        print(f"[notify] enviados={sent}")


if __name__ == "__main__":
    asyncio.run(main())
