"""Seed offline de la base de datos para maya-predice.

Crea el torneo 2026 y las 48 selecciones desde el mapeo canónico
(`team_mapping`). Útil para desarrollo sin red. La forma recomendada de poblar
partidos/grupos/resultados reales es la sincronización con la fuente oficial:

    python -m app.data.sync          # ingesta + verificación de cambios

Uso:
    python -m app.data.seed
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.data.team_mapping import TEAMS
from app.models.team import Team
from app.models.tournament import Tournament


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Tournament).where(Tournament.year == 2026))
        if existing.scalar_one_or_none() is None:
            db.add(Tournament(name="Copa Mundial de la FIFA 2026", year=2026, num_teams=48))

        existing_codes = set((await db.execute(select(Team.code))).scalars().all())
        added = 0
        for name, (code, conf) in TEAMS.items():
            if code not in existing_codes:
                db.add(Team(name=name, code=code, confederation=conf))
                added += 1

        await db.commit()
        print(f"Seed completado: torneo 2026 + {added} selecciones nuevas.")


if __name__ == "__main__":
    asyncio.run(seed())
