"""Tests de la configuración editable (coerción, clamp y roundtrip guardar/aplicar)."""

from __future__ import annotations

import asyncio

import pytest

from app.core.config import settings
from app.services.app_settings import _SPECS, _coerce, apply_overrides, effective_config, save_overrides


def test_coerce_bool():
    spec = _SPECS["hourly_refresh_enabled"]
    assert _coerce(spec, "true") is True
    assert _coerce(spec, "on") is True
    assert _coerce(spec, "false") is False
    assert _coerce(spec, "0") is False


def test_coerce_clamps_to_range():
    assert _coerce(_SPECS["ensemble_model_weight"], "1.5") == 1.0   # max
    assert _coerce(_SPECS["ensemble_model_weight"], "-0.3") == 0.0  # min
    assert _coerce(_SPECS["hourly_refresh_minutes"], "2") == 5      # min int


def test_effective_config_hides_secret():
    cfg = {c["key"]: c for c in effective_config()}
    assert cfg["odds_api_key"]["secret"] is True
    assert cfg["odds_api_key"]["value"] == ""
    assert "is_set" in cfg["odds_api_key"]


def test_save_and_apply_roundtrip():
    pytest.importorskip("aiosqlite")
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    import app.models  # noqa: F401 — registra AppSetting en Base.metadata
    from app.core.database import Base

    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        orig_w = settings.ensemble_model_weight
        orig_src = settings.player_sources
        try:
            async with session_maker() as db:
                await save_overrides(
                    db, {"ensemble_model_weight": "0.65", "player_sources": "wikipedia,wikidata"}
                )
            assert settings.ensemble_model_weight == 0.65
            assert settings.player_sources == "wikipedia,wikidata"

            # Simula otro worker: vuelve al valor viejo y reaplica desde la DB.
            object.__setattr__(settings, "ensemble_model_weight", 0.1)
            async with session_maker() as db:
                await apply_overrides(db)
            assert settings.ensemble_model_weight == 0.65
        finally:
            object.__setattr__(settings, "ensemble_model_weight", orig_w)
            object.__setattr__(settings, "player_sources", orig_src)

    asyncio.run(scenario())
