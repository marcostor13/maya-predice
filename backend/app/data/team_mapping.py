"""Mapeo canónico de las 48 selecciones del Mundial 2026.

Fuente de verdad para nombre -> (código FIFA, confederación). El nombre coincide
con el usado por el proveedor de datos oficial (openfootball / FIFA). Si el
proveedor usa otro alias, añádelo en ALIASES.
"""

from __future__ import annotations

# nombre oficial -> (código FIFA de 3 letras, confederación)
TEAMS: dict[str, tuple[str, str]] = {
    "Algeria": ("ALG", "CAF"),
    "Argentina": ("ARG", "CONMEBOL"),
    "Australia": ("AUS", "AFC"),
    "Austria": ("AUT", "UEFA"),
    "Belgium": ("BEL", "UEFA"),
    "Bosnia & Herzegovina": ("BIH", "UEFA"),
    "Brazil": ("BRA", "CONMEBOL"),
    "Canada": ("CAN", "CONCACAF"),
    "Cape Verde": ("CPV", "CAF"),
    "Colombia": ("COL", "CONMEBOL"),
    "Croatia": ("CRO", "UEFA"),
    "Curaçao": ("CUW", "CONCACAF"),
    "Czech Republic": ("CZE", "UEFA"),
    "DR Congo": ("COD", "CAF"),
    "Ecuador": ("ECU", "CONMEBOL"),
    "Egypt": ("EGY", "CAF"),
    "England": ("ENG", "UEFA"),
    "France": ("FRA", "UEFA"),
    "Germany": ("GER", "UEFA"),
    "Ghana": ("GHA", "CAF"),
    "Haiti": ("HAI", "CONCACAF"),
    "Iran": ("IRN", "AFC"),
    "Iraq": ("IRQ", "AFC"),
    "Ivory Coast": ("CIV", "CAF"),
    "Japan": ("JPN", "AFC"),
    "Jordan": ("JOR", "AFC"),
    "Mexico": ("MEX", "CONCACAF"),
    "Morocco": ("MAR", "CAF"),
    "Netherlands": ("NED", "UEFA"),
    "New Zealand": ("NZL", "OFC"),
    "Norway": ("NOR", "UEFA"),
    "Panama": ("PAN", "CONCACAF"),
    "Paraguay": ("PAR", "CONMEBOL"),
    "Portugal": ("POR", "UEFA"),
    "Qatar": ("QAT", "AFC"),
    "Saudi Arabia": ("KSA", "AFC"),
    "Scotland": ("SCO", "UEFA"),
    "Senegal": ("SEN", "CAF"),
    "South Africa": ("RSA", "CAF"),
    "South Korea": ("KOR", "AFC"),
    "Spain": ("ESP", "UEFA"),
    "Sweden": ("SWE", "UEFA"),
    "Switzerland": ("SUI", "UEFA"),
    "Tunisia": ("TUN", "CAF"),
    "Turkey": ("TUR", "UEFA"),
    "USA": ("USA", "CONCACAF"),
    "Uruguay": ("URU", "CONMEBOL"),
    "Uzbekistan": ("UZB", "AFC"),
}

# Alias del proveedor -> nombre canónico (por si una fuente usa otra grafía).
ALIASES: dict[str, str] = {
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Türkiye": "Turkey",
    "Côte d'Ivoire": "Ivory Coast",
    "United States": "USA",
    # Grafías del dataset histórico (martj42/international_results)
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Republic of Ireland": "Ireland",
}


def resolve_team(name: str) -> tuple[str, str, str] | None:
    """Devuelve (nombre_canónico, código, confederación) o None si es placeholder."""
    canonical = ALIASES.get(name, name)
    data = TEAMS.get(canonical)
    if data is None:
        return None
    return canonical, data[0], data[1]


def is_real_team(name: str) -> bool:
    return resolve_team(name) is not None


def resolve_history_team(name: str) -> str | None:
    """Identificador para entrenamiento: código FIFA si es una de las 48, si no None."""
    r = resolve_team(name)
    return r[1] if r else None
