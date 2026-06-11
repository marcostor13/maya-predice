"""Aviso a los buscadores vía IndexNow (Bing, Yandex, etc.).

`ping_indexnow(urls)` notifica que unas URLs cambiaron, para acelerar su rastreo.
Es no-op si no hay `indexnow_key` configurada. Defensivo ante errores de red (el
agente no debe romperse porque el ping falle).
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger("maya.growth.indexnow")

_ENDPOINT = "https://api.indexnow.org/indexnow"


async def ping_indexnow(urls: list[str], *, timeout: float = 20.0) -> bool:
    """Avisa a IndexNow de las URLs cambiadas. Devuelve True si el ping se aceptó."""
    key = settings.indexnow_key
    if not key:
        logger.info("IndexNow sin clave (INDEXNOW_KEY vacío); no se hace ping.")
        return False
    if not urls:
        return False

    site = settings.public_site_url.rstrip("/")
    host = urlparse(site).netloc
    if not host:
        logger.warning("PUBLIC_SITE_URL inválida (%r); no se hace ping a IndexNow.", site)
        return False

    body = {
        "host": host,
        "key": key,
        "keyLocation": f"{site}/{key}.txt",
        "urlList": urls,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(_ENDPOINT, json=body)
        if resp.status_code >= 400:
            logger.warning("IndexNow respondió %s: %s", resp.status_code, resp.text[:200])
            return False
        logger.info("IndexNow notificado de %s URLs (%s).", len(urls), resp.status_code)
        return True
    except httpx.HTTPError as exc:
        logger.warning("No se pudo avisar a IndexNow: %s", exc)
        return False
