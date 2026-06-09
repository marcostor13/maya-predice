"""Entrena el modelo y persiste las fuerzas por equipo desde la CLI.

    python -m app.data.train

Descarga el histórico internacional, lo combina con los resultados ya jugados del
torneo, ajusta el modelo Dixon-Coles y guarda ataque/defensa en `team_strengths`.
"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.prediction.training import persist_team_strengths, train_model


async def main() -> None:
    async with AsyncSessionLocal() as db:
        model = await train_model(db, force=True)
        saved = await persist_team_strengths(db, model)
        await db.commit()
        print(
            f"[train] equipos={len(model.teams)} "
            f"ventaja_local={model.home_advantage:.3f} rho={model.rho:.3f} "
            f"fuerzas_guardadas={saved}"
        )
        # Top 5 selecciones por ataque (control rápido de cordura).
        top = sorted(model.attack.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print("[train] top ataque:", ", ".join(f"{c}={v:.2f}" for c, v in top))


if __name__ == "__main__":
    asyncio.run(main())
