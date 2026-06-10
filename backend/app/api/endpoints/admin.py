"""Panel de administración: ejecuta las operaciones de mantenimiento por HTTP.

Protegido por token (`ADMIN_TOKEN`): el frontend lo envía en la cabecera
`X-Admin-Token`. Si no hay token configurado, el panel queda deshabilitado (503).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.cache import ApiCache
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.simulation import SimulationRun
from app.models.subscriber import Subscriber
from app.models.team import Team


def require_admin(x_admin_token: str | None = Header(None, alias="X-Admin-Token")) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="Panel de admin deshabilitado: define ADMIN_TOKEN.")
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Token de administrador inválido.")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/check")
async def check():
    """Valida el token (lo usa el login del panel)."""
    return {"ok": True}


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    """Conteos del estado actual de los datos."""

    async def count(model) -> int:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()

    finished = (
        await db.execute(
            select(func.count()).select_from(Match).where(Match.status == MatchStatus.FINISHED)
        )
    ).scalar_one()
    last_sim = (
        await db.execute(select(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    active_subs = (
        await db.execute(
            select(func.count()).select_from(Subscriber).where(Subscriber.active.is_(True))
        )
    ).scalar_one()
    return {
        "teams": await count(Team),
        "matches": await count(Match),
        "matches_finished": finished,
        "predictions": await count(Prediction),
        "subscribers_active": active_subs,
        "api_cache_rows": await count(ApiCache),
        "last_simulation": last_sim.created_at.isoformat() if last_sim else None,
        "model_version": settings.model_version,
    }


@router.post("/sync")
async def admin_sync(db: AsyncSession = Depends(get_db)):
    from app.services.sync_service import default_provider, sync_official_data

    run = await sync_official_data(db, default_provider(), trigger="admin")
    return {"ok": True, "message": run.message}


@router.post("/recompute")
async def admin_recompute(db: AsyncSession = Depends(get_db)):
    from app.services.recompute import recompute_pipeline

    return await recompute_pipeline(db, trigger="admin", force=True)


@router.post("/train")
async def admin_train(db: AsyncSession = Depends(get_db)):
    from app.services.prediction.training import persist_team_strengths, train_model

    model = await train_model(db, force=True)
    saved = await persist_team_strengths(db, model)
    return {
        "ok": True,
        "teams": len(model.teams),
        "home_advantage": round(model.home_advantage, 4),
        "rho": round(model.rho, 4),
        "strengths_saved": saved,
    }


@router.post("/simulate")
async def admin_simulate(db: AsyncSession = Depends(get_db)):
    from app.services.prediction_service import train_model
    from app.services.simulation_service import run_simulation

    model = await train_model(db)
    run = await run_simulation(db, model, trigger="admin")
    return {"ok": True, "iterations": run.iterations, "teams": getattr(run, "result_count", 0)}


@router.post("/squads")
async def admin_squads(db: AsyncSession = Depends(get_db)):
    from app.services.squad_service import build_player_providers, sync_squads

    providers = build_player_providers()
    if not providers:
        raise HTTPException(status_code=409, detail="No hay fuentes de plantillas configuradas (PLAYER_SOURCES).")
    run = await sync_squads(db, providers, trigger="admin")
    return {"ok": True, "sources": [p.name for p in providers], "message": run.message}


@router.post("/notify")
async def admin_notify(db: AsyncSession = Depends(get_db)):
    from app.services.notifications import notify_subscribers

    sent = await notify_subscribers(db, only_with_results=False)
    return {"ok": True, "sent": sent}


@router.post("/bootstrap")
async def admin_bootstrap():
    from app.data.bootstrap import run as bootstrap_run

    await bootstrap_run(force=True)
    return {"ok": True, "message": "Carga inicial ejecutada (partidos, modelo, predicciones, simulación, plantillas)."}


@router.get("/backtest")
async def admin_backtest():
    from app.services.prediction.backtest import run_backtest

    try:
        result = await run_backtest()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.to_dict()
