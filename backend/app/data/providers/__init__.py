"""Proveedores de datos oficiales del Mundial.

Abstracción `DataProvider`: cualquier fuente (openfootball, API-Football, etc.)
implementa `fetch_matches()` devolviendo una lista de `ProviderMatch` normalizada.
Esto permite cambiar de fuente sin tocar el servicio de sincronización.
"""

from app.data.providers.base import DataProvider, ProviderMatch
from app.data.providers.openfootball import OpenFootballProvider

__all__ = ["DataProvider", "ProviderMatch", "OpenFootballProvider"]
