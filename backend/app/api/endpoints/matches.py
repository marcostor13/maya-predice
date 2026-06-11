from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.data.venues import lookup
from app.models.match import Match, MatchStage, MatchStatus
from app.schemas.match import LiveMatchRead, MatchCreate, MatchRead, VenueDetail

router = APIRouter(prefix="/matches", tags=["matches"])


def _to_read(match: Match) -> MatchRead:
    read = MatchRead.model_validate(match)
    venue = lookup(match.venue)
    if venue:
        read.venue_detail = VenueDetail(**asdict(venue))
    return read


def _to_live_read(match: Match) -> LiveMatchRead:
    """Resuelve code/name desde las relaciones Team (cargadas con selectinload)."""
    home = match.home_team
    away = match.away_team
    return LiveMatchRead(
        id=match.id,
        home_code=home.code if home else None,
        home_name=home.name if home else None,
        away_code=away.code if away else None,
        away_name=away.name if away else None,
        home_goals=match.home_goals,
        away_goals=match.away_goals,
        minute=match.minute,
        status=match.status,
        kickoff=match.kickoff,
        group=match.group,
        stage=match.stage,
        venue=match.venue,
        home_placeholder=match.home_placeholder,
        away_placeholder=match.away_placeholder,
    )


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
    return [_to_read(m) for m in (await db.execute(stmt)).scalars().all()]


@router.get("/live", response_model=list[LiveMatchRead])
async def list_live_matches(db: AsyncSession = Depends(get_db)):
    """Partidos actualmente en juego, ordenados por kickoff."""
    stmt = (
        select(Match)
        .where(Match.status == MatchStatus.LIVE)
        .order_by(Match.kickoff)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
    )
    return [_to_live_read(m) for m in (await db.execute(stmt)).scalars().all()]


@router.get("/today", response_model=list[LiveMatchRead])
async def list_today_matches(db: AsyncSession = Depends(get_db)):
    """Partidos cuyo kickoff cae en el día UTC actual (cualquier estado)."""
    now = datetime.now(UTC)
    start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    stmt = (
        select(Match)
        .where(Match.kickoff >= start, Match.kickoff < end)
        .order_by(Match.kickoff)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
    )
    return [_to_live_read(m) for m in (await db.execute(stmt)).scalars().all()]


@router.get("/{match_id}", response_model=MatchRead)
async def get_match(match_id: int, db: AsyncSession = Depends(get_db)):
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return _to_read(match)


@router.post("", response_model=MatchRead, status_code=201)
async def create_match(payload: MatchCreate, db: AsyncSession = Depends(get_db)):
    match = Match(**payload.model_dump())
    db.add(match)
    await db.flush()
    return _to_read(match)
