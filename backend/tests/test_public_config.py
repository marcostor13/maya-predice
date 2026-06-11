"""Tests del endpoint público de configuración (afiliado)."""

from __future__ import annotations

import asyncio

from app.api.endpoints.config import public_config
from app.core.config import settings


def _reset():
    object.__setattr__(settings, "affiliate_enabled", False)
    object.__setattr__(settings, "affiliate_url", "")
    object.__setattr__(settings, "affiliate_label", "nuestra casa recomendada")


def test_url_hidden_when_disabled():
    _reset()
    object.__setattr__(settings, "affiliate_url", "https://casa.example?tag=me")
    try:
        r = asyncio.run(public_config())
        assert r["affiliate"]["enabled"] is False
        assert r["affiliate"]["url"] == ""  # no se expone si está desactivado
    finally:
        _reset()


def test_url_exposed_when_enabled():
    _reset()
    object.__setattr__(settings, "affiliate_enabled", True)
    object.__setattr__(settings, "affiliate_url", "https://casa.example?tag=me")
    object.__setattr__(settings, "affiliate_label", "Bet365")
    try:
        r = asyncio.run(public_config())
        assert r["affiliate"] == {
            "enabled": True,
            "url": "https://casa.example?tag=me",
            "label": "Bet365",
        }
    finally:
        _reset()
