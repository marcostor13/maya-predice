"""Cliente HTTP con reintentos suaves, compartido por los proveedores."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx


async def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    retries: int = 2,
    timeout: float = 30.0,
) -> Any:
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(retries + 1):
            try:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:  # red o JSON inválido
                last_exc = exc
                if attempt < retries:
                    await asyncio.sleep(2**attempt)
    raise RuntimeError(f"Fallo al consultar {url}: {last_exc}")
