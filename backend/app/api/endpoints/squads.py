from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.squad import Coach, Player, Position, SquadDiscrepancy
from app.models.team import Team
from app.schemas.squad import DiscrepancyRead, SquadRead
from app.services.squad_service import build_player_providers, sync_squads

router = APIRouter(prefix="/squads", tags=["squads"])

# Orden de posiciones para presentar la plantilla.
_POS_ORDER = {Position.GK: 0, Position.DEF: 1, Position.MID: 2, Position.FWD: 3, Position.UNKNOWN: 4}


@router.get("/discrepancies", response_model=list[DiscrepancyRead])
async def list_discrepancies(
    team_code: str | None = None, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """Conflictos detectados entre fuentes (control de veracidad)."""
    stmt = select(SquadDiscrepancy).order_by(desc(SquadDiscrepancy.created_at)).limit(limit)
    if team_code:
        stmt = stmt.where(SquadDiscrepancy.team_code == team_code.upper())
    return list((await db.execute(stmt)).scalars().all())


@router.post("/sync")
async def trigger_squad_sync(db: AsyncSession = Depends(get_db)):
    """Lanza una sincronización manual de plantillas (consenso multi-fuente)."""
    providers = build_player_providers()
    if not providers:
        raise HTTPException(status_code=409, detail="No hay fuentes de plantillas configuradas.")
    run = await sync_squads(db, providers, trigger="manual")
    return {"status": run.status.value, "message": run.message}


@router.get("/{team_code}", response_model=SquadRead)
async def get_squad(team_code: str, db: AsyncSession = Depends(get_db)):
    """Plantilla completa de una selección: jugadores, suplentes y entrenador."""
    team = (
        await db.execute(select(Team).where(Team.code == team_code.upper()))
    ).scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=404, detail="Selección no encontrada")

    players = list(
        (await db.execute(select(Player).where(Player.team_id == team.id))).scalars().all()
    )
    players.sort(key=lambda p: (_POS_ORDER.get(p.position, 4), p.shirt_number or 99))
    coach = (
        await db.execute(select(Coach).where(Coach.team_id == team.id))
    ).scalar_one_or_none()

    return SquadRead(team_code=team.code, team_name=team.name, coach=coach, players=players)
