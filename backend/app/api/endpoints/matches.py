import re
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.data.live.base import LiveFixture
from app.data.venues import lookup
from app.models.match import Match, MatchStage, MatchStatus
from app.schemas.match import (
    LiveIngestBody,
    LiveMatchRead,
    MatchCreate,
    MatchRead,
    VenueDetail,
)
from app.services.live_scores import sync_live_scores

router = APIRouter(prefix="/matches", tags=["matches"])

# Límites defensivos para la ingesta pública (cliente no confiable).
_MAX_INGEST_FIXTURES = 40
_MAX_GOALS = 30
_CODE_RE = re.compile(r"^[A-Z]{3}$")


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


def _goals_in_range(value: int | None) -> int | None:
    """Descarta goles fuera de 0..30 (dato del cliente no confiable)."""
    if value is None or value < 0 or value > _MAX_GOALS:
        return None
    return value


@router.post("/live-ingest")
async def live_ingest(payload: LiveIngestBody, db: AsyncSession = Depends(get_db)):
    """Ingesta pública de marcadores en vivo, alimentada por el cliente.

    El navegador trae el marcador de ESPN vía el proxy de Netlify (el backend no
    alcanza la fuente por la allowlist de Coolify) y lo envía aquí. Persistimos el
    marcador y, en la transición a finalizado, disparamos un recálculo serializado.

    openfootball sigue siendo la fuente **autoritativa** del resultado final: si un
    dato del cliente difiere, la siguiente sincronización oficial lo corrige (y el
    blindaje de `sync_official_data` evita que openfootball, que va con retraso,
    borre un marcador en vivo). El impacto de un dato erróneo es temporal y mínimo
    (el modelo se entrena con ~49k partidos históricos), el recálculo está
    serializado (un job a la vez) y solo se dispara al finalizar un partido.
    """
    fixtures = payload.fixtures
    if len(fixtures) > _MAX_INGEST_FIXTURES:
        return {"updated": 0, "live": 0, "finished": 0, "skipped": True}

    converted: list[LiveFixture] = []
    for fx in fixtures:
        home = fx.home_code.strip().upper()
        away = fx.away_code.strip().upper()
        if not _CODE_RE.match(home) or not _CODE_RE.match(away):
            continue
        converted.append(
            LiveFixture(
                home_code=home,
                away_code=away,
                home_name=None,
                away_name=None,
                kickoff_date=fx.kickoff_date,
                minute=fx.minute,
                status=fx.status or ("FT" if fx.finished else "LIVE"),
                home_goals=_goals_in_range(fx.home_goals),
                away_goals=_goals_in_range(fx.away_goals),
                finished=fx.finished,
            )
        )

    return await sync_live_scores(db, fixtures=converted)


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
