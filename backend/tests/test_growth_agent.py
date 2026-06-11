"""Tests del agente de crecimiento (sin red real).

Usa SQLite en memoria (aiosqlite); si no está instalado, se omite. Mockea
`deepseek.chat`, `ping_indexnow` y `send_growth_report` para no tocar la red ni
enviar emails. Verifica: el parseo crea GrowthInsight, la monetización siempre
requiere aprobación, y sin API key el ciclo termina en error sin crashear.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registra los modelos en Base.metadata
from app.core.config import settings
from app.core.database import Base
from app.models.growth import GrowthInsight, GrowthRun
from app.services.growth import agent

_SAMPLE_JSON = """{
  "insights": [
    {"category": "promotion", "title": "Hilo en X con el favorito",
     "body": "Publicar un hilo diario", "priority": 1,
     "action_type": "social_post", "content": "🏆 El favorito hoy es..."},
    {"category": "monetization", "title": "Probar banner extra",
     "body": "Añadir un slot de AdSense", "priority": 2,
     "requires_approval": false, "action_type": "email_only"},
    {"category": "content", "title": "Artículo de previa de grupos",
     "body": "Previa con datos", "priority": 3, "action_type": "seo_suggestion"}
  ]
}"""


async def _setup() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return session_maker


def test_cycle_parses_insights_and_forces_monetization_approval(monkeypatch):
    async def scenario():
        session_maker = await _setup()

        async def fake_chat(messages, **kwargs):
            return _SAMPLE_JSON

        sent: list[str] = []

        async def fake_send(subject, html, to_email):
            sent.append(to_email)
            return True

        monkeypatch.setattr(agent.deepseek, "chat", fake_chat)
        monkeypatch.setattr(agent, "send_growth_report", fake_send)
        object.__setattr__(settings, "deepseek_api_key", "test-key")
        object.__setattr__(settings, "indexnow_key", "")  # no IndexNow en el test
        object.__setattr__(settings, "growth_report_email", "owner@example.com")

        try:
            async with session_maker() as db:
                result = await agent.run_growth_cycle(db, trigger="test")

            assert result["status"] == "done"
            assert result["insights"] == 3

            async with session_maker() as db:
                insights = (await db.execute(select(GrowthInsight))).scalars().all()
                runs = (await db.execute(select(GrowthRun))).scalars().all()

            assert len(insights) == 3
            assert len(runs) == 1 and runs[0].status == "done"
            by_cat = {i.category: i for i in insights}
            # La monetización SIEMPRE requiere aprobación, aunque el modelo dijera false.
            assert by_cat["monetization"].requires_approval is True
            assert by_cat["promotion"].requires_approval is False
            # El contenido listo para publicar se guarda en payload.
            assert by_cat["promotion"].payload["content"].startswith("🏆")
            # Se envió el digest al dueño y los insights quedan "emailed".
            assert sent == ["owner@example.com"]
            assert all(i.status == "emailed" for i in insights)
        finally:
            object.__setattr__(settings, "deepseek_api_key", "")

    asyncio.run(scenario())


def test_cycle_without_api_key_ends_in_error(monkeypatch):
    async def scenario():
        session_maker = await _setup()

        sent: list[str] = []

        async def fake_send(subject, html, to_email):
            sent.append(subject)
            return True

        async def fail_chat(messages, **kwargs):  # no debe llamarse
            raise AssertionError("No se debe llamar a DeepSeek sin API key.")

        monkeypatch.setattr(agent.deepseek, "chat", fail_chat)
        monkeypatch.setattr(agent, "send_growth_report", fake_send)
        object.__setattr__(settings, "deepseek_api_key", "")
        object.__setattr__(settings, "growth_report_email", "owner@example.com")

        async with session_maker() as db:
            result = await agent.run_growth_cycle(db, trigger="test")

        assert result["status"] == "error"
        assert result["reason"] == "deepseek_not_configured"

        async with session_maker() as db:
            runs = (await db.execute(select(GrowthRun))).scalars().all()
        assert len(runs) == 1 and runs[0].status == "error"
        # Se avisó por email de que falta configurar la key.
        assert sent and "DEEPSEEK_API_KEY" in sent[0]

    asyncio.run(scenario())


def test_dedup_skips_recent_duplicate_titles(monkeypatch):
    async def scenario():
        session_maker = await _setup()

        async def fake_chat(messages, **kwargs):
            return _SAMPLE_JSON

        async def fake_send(subject, html, to_email):
            return True

        monkeypatch.setattr(agent.deepseek, "chat", fake_chat)
        monkeypatch.setattr(agent, "send_growth_report", fake_send)
        object.__setattr__(settings, "deepseek_api_key", "test-key")
        object.__setattr__(settings, "indexnow_key", "")

        try:
            async with session_maker() as db:
                await agent.run_growth_cycle(db, trigger="test")
            # Segundo ciclo con los MISMOS títulos: deben deduplicarse.
            async with session_maker() as db:
                result = await agent.run_growth_cycle(db, trigger="test")
            assert result["insights"] == 0
        finally:
            object.__setattr__(settings, "deepseek_api_key", "")

    asyncio.run(scenario())
