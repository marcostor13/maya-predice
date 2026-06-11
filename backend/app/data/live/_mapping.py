"""Utilidades compartidas por los proveedores de marcadores en vivo.

Centraliza el índice nombre-normalizado -> código FIFA (construido desde
`team_mapping`) y el parseo de fechas ISO, para que todas las fuentes
(ESPN/TheSportsDB/Google/API-Football) los compartan sin duplicar lógica.
"""

from __future__ import annotations

from datetime import date

from app.data.team_mapping import ALIASES, TEAMS, resolve_team

# Índice nombre-normalizado -> código (incluye alias del proveedor).
_NAME_TO_CODE: dict[str, str] = {}
for _name, (_code, _conf) in TEAMS.items():
    _NAME_TO_CODE[_name.strip().lower()] = _code
for _alias, _canonical in ALIASES.items():
    _resolved = resolve_team(_canonical)
    if _resolved:
        _NAME_TO_CODE[_alias.strip().lower()] = _resolved[1]


def code_for(name: str | None) -> str | None:
    """Devuelve el código FIFA de una selección por nombre (o None si no mapea)."""
    if not name:
        return None
    return _NAME_TO_CODE.get(name.strip().lower())


def parse_kickoff_date(value: str | None) -> date | None:
    """Parsea una fecha ISO-8601 (usa los primeros 10 caracteres). None si falla."""
    if not value:
        return None
    try:
        # ISO-8601, p. ej. "2026-06-11T19:00:00+00:00".
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
