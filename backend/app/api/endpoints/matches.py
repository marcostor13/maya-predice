from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.match import Match, MatchStage
from app.schemas.match import MatchCreate, MatchRead

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchRead])
async def list_matches(
    stage: MatchStage | None = None,
    group: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Match).order_by(Match.kickoff)
    if stage:
        stmt = stmt.where(Match.stage == stage)
    if group:
        stmt = stmt.where(Match.group == group)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{match_id}", response_model=MatchRead)
async def get_match(match_id: int, db: AsyncSession = Depends(get_db)):
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return match


@router.post("", response_model=MatchRead, status_code=201)
async def create_match(payload: MatchCreate, db: AsyncSession = Depends(get_db)):
    match = Match(**payload.model_dump())
    db.add(match)
    await db.flush()
    return match
