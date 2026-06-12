"""Tests del marcador en vivo (servicio + endpoints). SIN red.

Usa SQLite en memoria (aiosqlite); si no está, se omite. El proveedor live se
inyecta mockeado (no hay key ni red en el sandbox).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registra los modelos en Base.metadata
import app.services.live_scores as live_scores
from app.api.endpoints.matches import list_live_matches, list_today_matches
from app.core.config import settings
from app.core.database import Base
from app.data.live.base import LiveCandidate, LiveFixture
from app.models.match import Match, MatchStage, MatchStatus
from app.models.team import Team
from app.models.tournament import Tournament


async def _setup() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return session_maker


async def _seed_match(db: AsyncSession, *, status: MatchStatus = MatchStatus.SCHEDULED) -> Match:
    tour = Tournament(name="World Cup 2026", year=2026)
    db.add(tour)
    await db.flush()
    home = Team(name="Mexico", code="MEX", confederation="CONCACAF")
    away = Team(name="South Africa", code="RSA", confederation="CAF")
    db.add_all([home, away])
    await db.flush()
    match = Match(
        tournament_id=tour.id,
        external_ref="WC2026-001",
        home_team_id=home.id,
        away_team_id=away.id,
        stage=MatchStage.GROUP,
        group="A",
        venue="Mexico City",
        kickoff=datetime.now(UTC),
        status=status,
    )
    db.add(match)
    await db.flush()
    return match


class _FakeProvider:
    def __init__(self, fixtures: list[LiveFixture], name: str = "fake"):
        self._fixtures = fixtures
        self.name = name

    async def fetch_live(
        self, candidates: list[LiveCandidate] | None = None
    ) -> list[LiveFixture]:
        return self._fixtures


def _set(key: str, value: object) -> None:
    object.__setattr__(settings, key, value)


def test_live_update_sets_match_live(monkeypatch):
    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            match = await _seed_match(db)
            await db.commit()
            match_id = match.id

        fx = LiveFixture(
            home_code="MEX", away_code="RSA", home_name="Mexico", away_name="South Africa",
            kickoff_date=datetime.now(UTC).date(), minute=37, status="1H",
            home_goals=1, away_goals=0, finished=False,
        )
        _set("enable_live_scores", True)
        _set("live_source", "apifootball")
        _set("apifootball_key", "dummy")
        monkeypatch.setattr(live_scores, "apply_overrides", _noop_apply)
        monkeypatch.setattr(
            live_scores, "_build_providers", lambda: [_FakeProvider([fx])]
        )
        try:
            async with session_maker() as db:
                result = await live_scores.sync_live_scores(db)
            assert result["updated"] == 1
            assert result["live"] == 1
            assert result["finished"] == 0
            assert result["source"] == "fake"
            assert result["recompute_triggered"] is False
            async with session_maker() as db:
                m = await db.get(Match, match_id)
                assert m.status == MatchStatus.LIVE
                assert m.minute == 37
                assert m.home_goals == 1 and m.away_goals == 0
                assert m.live_updated_at is not None
        finally:
            _reset()

    asyncio.run(scenario())


def test_disabled_is_noop():
    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            await _seed_match(db)
            await db.commit()
        _set("enable_live_scores", False)
        try:
            async with session_maker() as db:
                result = await live_scores.sync_live_scores(db)
            assert result == {"updated": 0, "live": 0, "skipped": True}
        finally:
            _reset()

    asyncio.run(scenario())


def test_live_endpoint_serializes_codes_and_minute():
    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            await _seed_match(db, status=MatchStatus.LIVE)
            m = (await db.execute(_select_first_match())).scalars().first()
            m.minute = 55
            m.home_goals = 2
            m.away_goals = 1
            await db.commit()

        async with session_maker() as db:
            rows = await list_live_matches(db=db)
        assert len(rows) == 1
        row = rows[0]
        assert row.home_code == "MEX"
        assert row.home_name == "Mexico"
        assert row.away_code == "RSA"
        assert row.minute == 55
        assert row.status == MatchStatus.LIVE
        assert row.home_goals == 2 and row.away_goals == 1

        async with session_maker() as db:
            today_rows = await list_today_matches(db=db)
        assert len(today_rows) == 1
        assert today_rows[0].home_code == "MEX"

    asyncio.run(scenario())


def _select_first_match():
    from sqlalchemy import select

    return select(Match).order_by(Match.id)


async def _noop_apply(_db) -> None:
    return None


def test_fallback_uses_second_provider_when_first_empty(monkeypatch):
    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            match = await _seed_match(db)
            await db.commit()
            match_id = match.id

        fx = LiveFixture(
            home_code="MEX", away_code="RSA", home_name="Mexico", away_name="South Africa",
            kickoff_date=datetime.now(UTC).date(), minute=72, status="2H",
            home_goals=2, away_goals=2, finished=False,
        )
        empty = _FakeProvider([], name="espn")
        second = _FakeProvider([fx], name="thesportsdb")
        _set("enable_live_scores", True)
        _set("live_source", "espn,thesportsdb")
        monkeypatch.setattr(live_scores, "apply_overrides", _noop_apply)
        monkeypatch.setattr(live_scores, "_build_providers", lambda: [empty, second])
        try:
            async with session_maker() as db:
                result = await live_scores.sync_live_scores(db)
            assert result["source"] == "thesportsdb"
            assert result["updated"] == 1 and result["live"] == 1
            async with session_maker() as db:
                m = await db.get(Match, match_id)
                assert m.status == MatchStatus.LIVE
                assert m.minute == 72
                assert m.home_goals == 2 and m.away_goals == 2
        finally:
            _reset()

    asyncio.run(scenario())


def _reset() -> None:
    _set("enable_live_scores", False)
    _set("live_source", "espn,thesportsdb,google")
    _set("apifootball_key", "")
