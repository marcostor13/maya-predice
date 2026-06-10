"""Hash de contraseñas (PBKDF2) y JWT HS256, ambos con la librería estándar.

Sin dependencias externas: el hash usa `hashlib.pbkdf2_hmac` y el JWT se firma con
HMAC-SHA256. La contraseña se guarda como `pbkdf2_sha256$iteraciones$salt$hash`.
El JWT se firma con `JWT_SECRET` (o `ADMIN_TOKEN` como respaldo).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from app.core.config import settings

_ITERATIONS = 200_000


# ---------- contraseñas ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, expected = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(dk.hex(), expected)
    except (ValueError, AttributeError):
        return False


# ---------- JWT HS256 ----------

def _secret() -> str:
    return settings.jwt_secret or settings.admin_token


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def _sign(signing_input: str) -> str:
    sig = hmac.new(_secret().encode(), signing_input.encode(), hashlib.sha256).digest()
    return _b64url(sig)


def create_access_token(subject: str, hours: int = 12) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": now, "exp": now + hours * 3600}
    segments = [
        _b64url(json.dumps(header, separators=(",", ":")).encode()),
        _b64url(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    segments.append(_sign(".".join(segments)))
    return ".".join(segments)


def decode_token(token: str) -> dict | None:
    if not _secret():
        return None
    try:
        header_b64, payload_b64, sig = token.split(".")
        if not hmac.compare_digest(_sign(f"{header_b64}.{payload_b64}"), sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
