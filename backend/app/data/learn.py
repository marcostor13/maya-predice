"""Aprendizaje continuo desde la CLI (para cron externo, p. ej. en Coolify).

    python -m app.data.learn

Hace un ciclo completo: sincroniza plantillas multi-fuente (jugadores/lesiones/
fotos + DT) y luego reentrena el modelo con los datos frescos (reingesta de
resultados + cuotas → predicciones → simulación). Equivale al job horario del
scheduler interno, pero pensado para programarlo con el cron de Coolify cuando
`ENABLE_SCHEDULER=false`. Corre síncrono (un proceso que termina al acabar).
"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.recompute import recompute_pipeline
from app.services.squad_service import build_player_providers, sync_squads


async def main() -> None:
    providers = build_player_providers()
    if providers:
        async with AsyncSessionLocal() as db:
            try:
                run = await sync_squads(db, providers, trigger="cron")
                await db.commit()
                print(f"[learn] plantillas ({[p.name for p in providers]}): {run.message}")
            except Exception as exc:  # noqa: BLE001 — una fuente caída no aborta el reentreno
                await db.rollback()
                print(f"[learn] plantillas fallaron (se continúa): {exc}")

    async with AsyncSessionLocal() as db:
        summary = await recompute_pipeline(db, trigger="cron", force=True)
        await db.commit()
        print(f"[learn] recálculo: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
