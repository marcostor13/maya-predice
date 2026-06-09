from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.team import Team
from app.schemas.team import TeamCreate, TeamRead

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamRead])
async def list_teams(group: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Team).order_by(Team.name)
    if group:
        stmt = stmt.where(Team.group == group)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(team_id: int, db: AsyncSession = Depends(get_db)):
    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return team


@router.post("", response_model=TeamRead, status_code=201)
async def create_team(payload: TeamCreate, db: AsyncSession = Depends(get_db)):
    team = Team(**payload.model_dump())
    db.add(team)
    await db.flush()
    return team
