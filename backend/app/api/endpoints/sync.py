from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sync import DataChange, SyncRun
from app.schemas.sync import DataChangeRead, SyncRunRead
from app.services.sync_service import default_provider, sync_official_data

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/runs", response_model=list[SyncRunRead])
async def list_sync_runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Historial de verificaciones (diarias y manuales)."""
    stmt = select(SyncRun).order_by(desc(SyncRun.started_at)).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/changes", response_model=list[DataChangeRead])
async def list_changes(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Últimos cambios detectados respecto a la fuente oficial."""
    stmt = select(DataChange).order_by(desc(DataChange.created_at)).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/run", response_model=SyncRunRead)
async def trigger_sync(db: AsyncSession = Depends(get_db)):
    """Lanza una verificación manual inmediata contra la fuente oficial."""
    return await sync_official_data(db, default_provider(), trigger="manual")


@router.post("/recompute")
async def trigger_recompute(db: AsyncSession = Depends(get_db)):
    """Reingiere resultados y, si cambian, recalcula modelo, predicciones y simulación."""
    from app.services.recompute import recompute_pipeline

    return await recompute_pipeline(db, trigger="manual")
