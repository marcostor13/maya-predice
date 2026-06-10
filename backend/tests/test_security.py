"""Tests de hash de contraseñas y JWT (HS256, stdlib)."""

import time

from app.core import config
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("Cl4veSegura!")
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password("Cl4veSegura!", h)
    assert not verify_password("otra", h)


def test_password_hashes_are_salted():
    assert hash_password("x") != hash_password("x")  # salt aleatorio


def test_jwt_roundtrip(monkeypatch):
    monkeypatch.setattr(config.settings, "jwt_secret", "secreto-test")
    token = create_access_token("marcos", hours=1)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "marcos"


def test_jwt_rejects_tampered(monkeypatch):
    monkeypatch.setattr(config.settings, "jwt_secret", "secreto-test")
    token = create_access_token("marcos")
    assert decode_token(token + "x") is None
    assert decode_token("no.es.jwt") is None


def test_jwt_wrong_secret(monkeypatch):
    monkeypatch.setattr(config.settings, "jwt_secret", "secreto-A")
    token = create_access_token("marcos")
    monkeypatch.setattr(config.settings, "jwt_secret", "secreto-B")
    assert decode_token(token) is None


def test_jwt_expired(monkeypatch):
    monkeypatch.setattr(config.settings, "jwt_secret", "secreto-test")
    # token ya expirado (hours negativo)
    token = create_access_token("marcos", hours=-1)
    assert decode_token(token) is None
    assert time.time() > 0
