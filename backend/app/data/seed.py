"""Seed inicial de la base de datos para maya-predice.

Crea el torneo (Mundial 2026) y un conjunto base de selecciones. La lista de
equipos clasificados y la asignación final de grupos debe completarse cuando se
oficialice (ver PLATFORM.md). Aquí se incluyen los anfitriones y selecciones de
referencia para poder desarrollar y probar la lógica de extremo a extremo.

Uso:
    python -m app.data.seed
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.team import Team
from app.models.tournament import Tournament

# (nombre, código ISO-3, confederación, ranking FIFA aproximado)
SEED_TEAMS: list[tuple[str, str, str, int]] = [
    ("Argentina", "ARG", "CONMEBOL", 1),
    ("Francia", "FRA", "UEFA", 2),
    ("España", "ESP", "UEFA", 3),
    ("Inglaterra", "ENG", "UEFA", 4),
    ("Brasil", "BRA", "CONMEBOL", 5),
    ("Portugal", "POR", "UEFA", 6),
    ("Países Bajos", "NED", "UEFA", 7),
    ("Bélgica", "BEL", "UEFA", 8),
    ("Alemania", "GER", "UEFA", 9),
    ("Croacia", "CRO", "UEFA", 10),
    ("México", "MEX", "CONCACAF", 17),
    ("Estados Unidos", "USA", "CONCACAF", 16),
    ("Canadá", "CAN", "CONCACAF", 30),
    ("Uruguay", "URU", "CONMEBOL", 11),
    ("Colombia", "COL", "CONMEBOL", 12),
    ("Japón", "JPN", "AFC", 18),
    ("Marruecos", "MAR", "CAF", 14),
    ("Senegal", "SEN", "CAF", 19),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # Torneo
        existing = await db.execute(select(Tournament).where(Tournament.year == 2026))
        tournament = existing.scalar_one_or_none()
        if tournament is None:
            tournament = Tournament(name="Copa Mundial de la FIFA 2026", year=2026, num_teams=48)
            db.add(tournament)

        # Equipos (idempotente por código)
        existing_codes = set(
            (await db.execute(select(Team.code))).scalars().all()
        )
        for name, code, conf, rank in SEED_TEAMS:
            if code not in existing_codes:
                db.add(Team(name=name, code=code, confederation=conf, fifa_rank=rank))

        await db.commit()
        print(f"Seed completado: {len(SEED_TEAMS)} equipos de referencia + torneo 2026.")


if __name__ == "__main__":
    asyncio.run(seed())
