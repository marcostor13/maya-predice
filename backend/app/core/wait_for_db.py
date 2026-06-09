"""Espera a que la base de datos esté disponible antes de migrar/arrancar.

Reintenta la conexión con backoff e imprime mensajes claros (sin credenciales).
Si tras el tiempo límite no conecta, sale con código 1 y un error explícito —
útil para diagnosticar un `DATABASE_URL` mal puesto o una DB no creada.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


async def wait(timeout: float = 90.0) -> None:
    target = settings.database_url.split("@")[-1]  # oculta usuario:contraseña
    print(f"[wait-for-db] objetivo: {target}", flush=True)

    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    delay = 1.0
    while True:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("[wait-for-db] conexión a la base de datos OK", flush=True)
            await engine.dispose()
            return
        except Exception as exc:  # noqa: BLE001
            if loop.time() >= deadline:
                print(
                    f"[wait-for-db] ERROR: sin conexión tras {timeout:.0f}s. "
                    f"Revisa DATABASE_URL (host {target}). Detalle: {exc!r}",
                    flush=True,
                )
                await engine.dispose()
                sys.exit(1)
            print(
                f"[wait-for-db] aún no disponible ({type(exc).__name__}); reintentando…",
                flush=True,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 5.0)


if __name__ == "__main__":
    asyncio.run(wait())
