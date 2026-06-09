"""Pipeline de recálculo en vivo.

Reingiere los resultados oficiales y, **si hubo cambios** (partidos terminados,
marcadores, cruces resueltos), recalcula toda la cadena dependiente:
1. reentrena el modelo (las estadísticas cambian con cada resultado),
2. persiste las fuerzas por equipo,
3. regenera las predicciones de los partidos venideros,
4. re-ejecuta la simulación del torneo.

Pensado para ejecutarse periódicamente durante el Mundial (cada
`LIVE_POLL_MINUTES`): a medida que terminan partidos, la plataforma se actualiza
sola. Es eficiente: si no hubo cambios, no recalcula nada pesado.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prediction.training import persist_team_strengths, train_model
from app.services.prediction_service import regenerate_upcoming_predictions
from app.services.simulation_service import run_simulation
from app.services.sync_service import default_provider, sync_official_data

logger = logging.getLogger("maya.recompute")


async def recompute_pipeline(db: AsyncSession, *, trigger: str = "scheduled", force: bool = False) -> dict:
    """Sincroniza resultados y, si cambian, recalcula modelo, predicciones y simulación."""
    sync_run = await sync_official_data(db, default_provider(), trigger=trigger)
    await db.flush()

    changed = force or sync_run.created > 0 or sync_run.updated > 0
    summary = {
        "synced": sync_run.matches_seen,
        "created": sync_run.created,
        "updated": sync_run.updated,
        "changes": sync_run.changes_count,
        "recomputed": changed,
        "predictions": 0,
        "simulated_teams": 0,
    }
    if not changed:
        logger.info("Sin cambios en resultados; no se recalcula.")
        return summary

    model = await train_model(db, force=True)
    await persist_team_strengths(db, model)
    summary["predictions"] = await regenerate_upcoming_predictions(db, model)
    sim_run = await run_simulation(db, model, trigger=trigger)
    summary["simulated_teams"] = getattr(sim_run, "result_count", 0)
    logger.info(
        "Recálculo completo: %s predicciones, simulación reejecutada.",
        summary["predictions"],
    )
    return summary
