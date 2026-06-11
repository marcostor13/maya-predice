"""Cliente mínimo de DeepSeek (API OpenAI-compatible).

Expone `chat()` para pedir una respuesta al modelo. La clave se lee de
`settings.deepseek_api_key` (nunca se hardcodea). Si no hay clave, lanza
`DeepSeekNotConfigured` para que el pipeline aborte el ciclo con un log (y avise
por email) en lugar de romper. Usa httpx async, ya presente en el proyecto.
"""

from __future__ import annotations

import httpx

from app.core.config import settings


class DeepSeekError(RuntimeError):
    """Fallo al consultar la API de DeepSeek."""


class DeepSeekNotConfigured(DeepSeekError):
    """No hay API key configurada (DEEPSEEK_API_KEY)."""


async def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_json: bool = False,
    timeout: float = 60.0,
) -> str:
    """Llama a `{base_url}/chat/completions` y devuelve el `content` del 1er choice.

    `response_json=True` pide `response_format={"type":"json_object"}` (el modelo
    devuelve JSON válido). Lanza `DeepSeekNotConfigured` si falta la API key y
    `DeepSeekError` ante errores de red/respuesta.
    """
    api_key = settings.deepseek_api_key
    if not api_key:
        raise DeepSeekNotConfigured("Falta DEEPSEEK_API_KEY (configúrala en el panel o el entorno).")

    payload: dict = {
        "model": model or settings.deepseek_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_json:
        payload["response_format"] = {"type": "json_object"}

    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise DeepSeekError(f"Fallo al consultar DeepSeek: {exc}") from exc
    except ValueError as exc:  # JSON inválido
        raise DeepSeekError(f"Respuesta no-JSON de DeepSeek: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekError(f"Respuesta de DeepSeek con formato inesperado: {data!r}") from exc
