"""Tests de la ingesta de marcadores desde el navegador + blindaje del sync. SIN red.

Usa SQLite en memoria (aiosqlite); si no está, se omite. `start_job` se mockea para
no ejecutar el pipeline pesado ni tocar la red.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registra los modelos en Base.metadata
import app.services.jobs as jobs
import app.services.live_scores as live_scores
from app.api.endpoints.matches import live_ingest
from app.core.database import Base
from app.data.providers.base import ProviderMatch
from app.models.match import Match, MatchStage, MatchStatus
from app.models.team import Team
from app.models.tournament import Tournament
from app.schemas.match import LiveIngestBody, LiveIngestFixture
from app.services.sync_service import _apply, _existing_match_to_dict, _provider_match_to_dict


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
    home = Team(name="Argentina", code="ARG", confederation="CONMEBOL")
    away = Team(name="Brazil", code="BRA", confederation="CONMEBOL")
    db.add_all([home, away])
    await db.flush()
    match = Match(
        tournament_id=tour.id,
        external_ref="WC2026-ARGBRA",
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


async def _noop_apply(_db) -> None:
    return None


def test_ingest_finishes_match_and_triggers_recompute_once(monkeypatch):
    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            match = await _seed_match(db)
            await db.commit()
            match_id = match.id

        calls: list[str] = []

        async def fake_start_job(db, name, work, *, trigger="admin"):
            calls.append(name)
            return None

        monkeypatch.setattr(live_scores, "apply_overrides", _noop_apply)
        monkeypatch.setattr(jobs, "start_job", fake_start_job)

        body = LiveIngestBody(
            fixtures=[
                LiveIngestFixture(
                    home_code="arg",
                    away_code="bra",
                    kickoff_date=datetime.now(UTC).date(),
                    minute=90,
                    status="FT",
                    home_goals=2,
                    away_goals=1,
                    finished=True,
                )
            ]
        )

        async with session_maker() as db:
            result = await live_ingest(body, db=db)

        assert result["finished"] == 1
        assert result["recompute_triggered"] is True
        assert calls == ["recompute"]

        async with session_maker() as db:
            m = await db.get(Match, match_id)
            assert m.status == MatchStatus.FINISHED
            assert m.home_goals == 2 and m.away_goals == 1

        # Segunda ingesta idéntica: ya estaba FINISHED → NO vuelve a disparar.
        calls.clear()
        async with session_maker() as db:
            result2 = await live_ingest(body, db=db)
        assert result2["finished"] == 1  # se cuenta como actualización
        assert result2["recompute_triggered"] is False
        assert calls == []

    asyncio.run(scenario())


def test_ingest_discards_invalid_codes_and_goals(monkeypatch):
    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            await _seed_match(db)
            await db.commit()

        monkeypatch.setattr(live_scores, "apply_overrides", _noop_apply)

        # Códigos no válidos y goles fuera de rango: el fixture válido sobrevive,
        # con goles fuera de rango puestos a None (queda LIVE, no FINISHED).
        body = LiveIngestBody(
            fixtures=[
                LiveIngestFixture(home_code="XX", away_code="YY"),  # códigos inválidos
                LiveIngestFixture(
                    home_code="ARG",
                    away_code="BRA",
                    minute=10,
                    home_goals=99,  # fuera de rango -> None
                    away_goals=0,
                    finished=False,
                ),
            ]
        )

        async with session_maker() as db:
            result = await live_ingest(body, db=db)
        assert result["live"] == 1
        assert result["finished"] == 0
        assert result["recompute_triggered"] is False

    asyncio.run(scenario())


def _provider_match(**overrides) -> ProviderMatch:
    base = {
        "external_ref": "WC2026-ARGBRA",
        "stage": MatchStage.GROUP,
        "matchday": 1,
        "group": "A",
        "home_name": "Argentina",
        "away_name": "Brazil",
        "home_code": "ARG",
        "away_code": "BRA",
        "home_confederation": "CONMEBOL",
        "away_confederation": "CONMEBOL",
        "home_placeholder": None,
        "away_placeholder": None,
        "kickoff": datetime.now(UTC),
        "venue": "Mexico City",
        "home_goals": None,
        "away_goals": None,
    }
    base.update(overrides)
    return ProviderMatch(**base)


def test_sync_does_not_degrade_finished_match():
    """openfootball sin resultado NO debe borrar un marcador ya finalizado."""

    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            match = await _seed_match(db, status=MatchStatus.FINISHED)
            match.home_goals = 3
            match.away_goals = 0
            await db.commit()
            match_id = match.id

        async with session_maker() as db:
            m = await db.get(Match, match_id)
            home = await db.get(Team, m.home_team_id)
            away = await db.get(Team, m.away_team_id)
            code_to_team = {home.code: home, away.code: away}
            id_to_code = {home.id: home.code, away.id: away.code}

            pm = _provider_match()  # sin goles (no terminado)
            old_state = _existing_match_to_dict(m, id_to_code)
            new_state = _provider_match_to_dict(pm, old_state)

            # El blindaje preserva goles/estado en el estado nuevo.
            assert new_state["home_goals"] == 3
            assert new_state["away_goals"] == 0
            assert new_state["status"] == MatchStatus.FINISHED.value

            # Y _apply tampoco los toca.
            _apply(m, pm, code_to_team)
            assert m.status == MatchStatus.FINISHED
            assert m.home_goals == 3 and m.away_goals == 0

    asyncio.run(scenario())


def test_sync_applies_final_result():
    """openfootball CON resultado sí actualiza un partido programado a finalizado."""

    async def scenario():
        session_maker = await _setup()
        async with session_maker() as db:
            match = await _seed_match(db, status=MatchStatus.SCHEDULED)
            await db.commit()
            match_id = match.id

        async with session_maker() as db:
            m = await db.get(Match, match_id)
            home = await db.get(Team, m.home_team_id)
            away = await db.get(Team, m.away_team_id)
            code_to_team = {home.code: home, away.code: away}

            pm = _provider_match(home_goals=1, away_goals=1)
            _apply(m, pm, code_to_team)
            assert m.status == MatchStatus.FINISHED
            assert m.home_goals == 1 and m.away_goals == 1

    asyncio.run(scenario())
