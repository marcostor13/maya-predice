"""Orquestación de la simulación Monte Carlo del torneo.

Construye los grupos desde la base de datos, aplica el modelo entrenado y los
ajustes por disponibilidad, corre la simulación y persiste las probabilidades por
selección (superar grupo, alcanzar cada ronda y ser campeón).
"""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.simulation import SimulationResult, SimulationRun
from app.models.team import Team
from app.services.prediction.dixon_coles import DixonColesModel
from app.services.prediction.simulator import TournamentSimulator
from app.services.prediction_service import compute_all_adjustments

logger = logging.getLogger("maya.simulation")


async def _build_groups(db: AsyncSession, model: DixonColesModel) -> tuple[dict, dict]:
    """Devuelve ({grupo: [códigos]}, {código: team_id}) para equipos del modelo."""
    teams = (await db.execute(select(Team).where(Team.group.is_not(None)))).scalars().all()
    groups: dict[str, list[str]] = defaultdict(list)
    code_to_id: dict[str, int] = {}
    for t in teams:
        if t.code in model.attack:  # solo equipos que el modelo conoce
            groups[t.group].append(t.code)
            code_to_id[t.code] = t.id
    return dict(groups), code_to_id


async def run_simulation(
    db: AsyncSession,
    model: DixonColesModel,
    *,
    trigger: str = "manual",
    iterations: int | None = None,
) -> SimulationRun:
    iters = iterations or settings.simulation_iterations
    groups, code_to_id = await _build_groups(db, model)
    if not groups:
        raise ValueError("No hay grupos con equipos para simular (¿faltan datos?).")

    adjustments = await compute_all_adjustments(db)
    simulator = TournamentSimulator(model, adjustments)
    probs = simulator.run(groups, iterations=iters)

    run = SimulationRun(
        model_version=settings.model_version, iterations=iters, trigger=trigger
    )
    db.add(run)
    await db.flush()

    saved = 0
    for code, p in probs.items():
        if code in code_to_id:
            db.add(
                SimulationResult(
                    run_id=run.id,
                    team_id=code_to_id[code],
                    advance_prob=p["advance"],
                    round16_prob=p["round16"],
                    quarter_prob=p["quarter"],
                    semi_prob=p["semi"],
                    final_prob=p["final"],
                    champion_prob=p["champion"],
                )
            )
            saved += 1
    run.result_count = saved  # atributo transitorio (no persistido) para el caller
    logger.info("Simulación: %s equipos, %s iteraciones.", saved, iters)
    return run
