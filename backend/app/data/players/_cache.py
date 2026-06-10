"""GET con caché persistente en base de datos.

Antes de llamar a la API externa busca la respuesta en `api_cache` por la clave de
la consulta (endpoint + parámetros, sin token). Si existe y no ha caducado, la
devuelve sin gastar una llamada. Si no, la pide, la guarda y la devuelve.

Así una misma consulta no se hace dos veces (ahorra créditos de Sportmonks).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.data.players._http import get_json
from app.models.cache import ApiCache

logger = logging.getLogger("maya.cache")


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def cached_get_json(
    url: str,
    *,
    cache_key: str,
    source: str = "",
    params: dict | None = None,
    headers: dict | None = None,
    ttl_hours: int = 24,
) -> Any:
    """Devuelve la respuesta JSON, usando la caché de la DB si está disponible.

    `cache_key` debe identificar la consulta SIN incluir el token (para no
    duplicar ni filtrar credenciales). `ttl_hours<=0` = caché indefinida.
    """
    h = _hash(cache_key)

    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(select(ApiCache).where(ApiCache.cache_key == h))
        ).scalar_one_or_none()
        if row is not None and row.response is not None:
            fresh = ttl_hours <= 0 or row.fetched_at > datetime.now(UTC) - timedelta(hours=ttl_hours)
            if fresh:
                logger.debug("cache HIT %s", cache_key)
                return row.response

    logger.debug("cache MISS %s -> llamando a la API", cache_key)
    data = await get_json(url, params=params, headers=headers)

    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(select(ApiCache).where(ApiCache.cache_key == h))
        ).scalar_one_or_none()
        if row is None:
            db.add(ApiCache(cache_key=h, source=source, request=cache_key, response=data))
        else:
            row.response = data
            row.source = source
        await db.commit()
    return data
