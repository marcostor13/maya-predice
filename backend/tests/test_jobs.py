"""Tests del gestor de trabajos en segundo plano (job runner del panel admin).

Usa SQLite en memoria (aiosqlite); si no está instalado, se omite (CI puro no lo
trae). Verifica: el job exitoso queda 'done' con resultado, el fallo queda 'error'
con mensaje, y no se permiten dos jobs a la vez.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registra los modelos en Base.metadata
import app.services.jobs as jobs
from app.core.database import Base


async def _setup() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    jobs.AsyncSessionLocal = session_maker  # el job de fondo usa esta DB
    return session_maker


def test_job_success_records_result():
    async def scenario():
        session_maker = await _setup()

        async def work(_session):
            await asyncio.sleep(0.01)
            return {"predictions": 42}

        async with session_maker() as db:
            await jobs.start_job(db, "recompute", work)
        await asyncio.sleep(0.1)
        async with session_maker() as db:
            d = jobs.job_to_dict(await jobs.latest_job(db, "recompute"))
        assert d["status"] == "done"
        assert d["result"] == {"predictions": 42}

    asyncio.run(scenario())


def test_job_failure_records_error():
    async def scenario():
        session_maker = await _setup()

        async def work(_session):
            raise RuntimeError("boom")

        async with session_maker() as db:
            await jobs.start_job(db, "recompute", work)
        await asyncio.sleep(0.1)
        async with session_maker() as db:
            d = jobs.job_to_dict(await jobs.latest_job(db, "recompute"))
        assert d["status"] == "error"
        assert "boom" in d["error"]

    asyncio.run(scenario())


def test_second_job_is_blocked_while_running():
    async def scenario():
        session_maker = await _setup()

        async def work(_session):
            await asyncio.sleep(0.1)
            return {}

        async with session_maker() as db:
            await jobs.start_job(db, "recompute", work)
        async with session_maker() as db:
            with pytest.raises(jobs.JobInProgress):
                await jobs.start_job(db, "recompute", work)
        await asyncio.sleep(0.15)

    asyncio.run(scenario())
