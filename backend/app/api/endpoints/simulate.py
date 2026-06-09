from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.simulation import SimulationResult, SimulationRun
from app.models.team import Team
from app.schemas.simulation import SimulationRead, TeamSimulationRead
from app.services.prediction_service import train_model
from app.services.simulation_service import run_simulation

router = APIRouter(prefix="/simulate", tags=["simulate"])


async def _serialize(db: AsyncSession, run: SimulationRun) -> SimulationRead:
    rows = (
        await db.execute(
            select(SimulationResult, Team)
            .join(Team, Team.id == SimulationResult.team_id)
            .where(SimulationResult.run_id == run.id)
            .order_by(desc(SimulationResult.champion_prob))
        )
    ).all()
    teams = [
        TeamSimulationRead(
            team_code=t.code,
            team_name=t.name,
            advance_prob=r.advance_prob,
            round16_prob=r.round16_prob,
            quarter_prob=r.quarter_prob,
            semi_prob=r.semi_prob,
            final_prob=r.final_prob,
            champion_prob=r.champion_prob,
        )
        for r, t in rows
    ]
    return SimulationRead(
        run_id=run.id,
        model_version=run.model_version,
        iterations=run.iterations,
        created_at=run.created_at,
        teams=teams,
    )


@router.get("/tournament", response_model=SimulationRead)
async def get_tournament_simulation(db: AsyncSession = Depends(get_db)):
    """Devuelve la última simulación del torneo (probabilidades por selección)."""
    run = (
        await db.execute(select(SimulationRun).order_by(desc(SimulationRun.created_at)).limit(1))
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Aún no hay simulación. Ejecuta /simulate/run.")
    return await _serialize(db, run)


@router.post("/run", response_model=SimulationRead)
async def run_tournament_simulation(db: AsyncSession = Depends(get_db)):
    """Entrena el modelo y ejecuta una nueva simulación Monte Carlo del torneo."""
    try:
        model = await train_model(db)
        run = await run_simulation(db, model, trigger="manual")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.flush()
    return await _serialize(db, run)
