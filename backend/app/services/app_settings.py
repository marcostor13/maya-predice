"""Configuración editable en runtime desde el panel admin.

Define **qué** ajustes operativos se pueden cambiar (`EDITABLE`), los persiste en
`app_settings` y los aplica sobre el `settings` en memoria. Como producción corre
2 workers Gunicorn (cada uno con su `settings`), los overrides se **recargan al
inicio de cada job** y al arrancar, de modo que ambos workers convergen al valor
guardado. Los hiperparámetros del modelo (ξ, filtro, prior) NO son editables: están
blindados a propósito (ver `config.py`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.app_setting import AppSetting

logger = logging.getLogger("maya.settings")


@dataclass(frozen=True)
class SettingSpec:
    key: str
    type: str  # bool | int | float | str
    group: str
    label: str
    desc: str
    secret: bool = False
    min: float | None = None
    max: float | None = None


# Ajustes operativos editables desde el panel (clave = atributo de `settings`).
EDITABLE: tuple[SettingSpec, ...] = (
    SettingSpec("hourly_refresh_enabled", "bool", "Aprendizaje continuo",
                "Cron horario activo",
                "Cada hora recopila de todas las fuentes y reentrena el modelo."),
    SettingSpec("hourly_refresh_minutes", "int", "Aprendizaje continuo",
                "Cada cuántos minutos",
                "Frecuencia del ciclo de aprendizaje (aplica del todo tras reiniciar).",
                min=5, max=1440),
    SettingSpec("enable_live_updates", "bool", "Actualización en vivo",
                "Polling en vivo activo",
                "Durante el torneo reingiere resultados y recalcula al terminar partidos."),
    SettingSpec("live_poll_minutes", "int", "Actualización en vivo",
                "Cada cuántos minutos",
                "Frecuencia del chequeo de resultados (bájalo durante los partidos).",
                min=5, max=1440),
    SettingSpec("enable_live_scores", "bool", "En vivo",
                "Marcador en vivo activo",
                "Refresca el marcador (goles/minuto) in-play, sin recalcular predicciones. "
                "Requiere allowlistar en Coolify los hosts de las fuentes: "
                "site.api.espn.com, www.thesportsdb.com, www.google.com."),
    SettingSpec("live_scores_minutes", "int", "En vivo",
                "Cada cuántos minutos",
                "Frecuencia de la ingesta del marcador en vivo (se aplica al guardar).",
                min=1, max=15),
    SettingSpec("live_source", "str", "En vivo",
                "Fuente del marcador",
                "Fuentes live separadas por coma, en orden de prioridad (cadena de fallback): "
                "espn,thesportsdb,google,apifootball. Allowlistar en Coolify el host de cada "
                "fuente usada (espn=site.api.espn.com, google=www.google.com, "
                "thesportsdb=www.thesportsdb.com)."),
    SettingSpec("apifootball_key", "str", "En vivo",
                "API key de API-Football",
                "Clave de api-football.com (x-apisports-key). Déjalo vacío para no cambiarla.",
                secret=True),
    SettingSpec("enable_market_ensemble", "bool", "Cuotas de mercado",
                "Ensamble con el mercado",
                "Mezcla la predicción 1X2 con las cuotas (la señal más precisa)."),
    SettingSpec("ensemble_model_weight", "float", "Cuotas de mercado",
                "Peso del modelo (ω)",
                "ω=peso del modelo; el mercado pesa 1−ω. 0.4 = el mercado manda.",
                min=0.0, max=1.0),
    SettingSpec("odds_api_key", "str", "Cuotas de mercado",
                "API key de The Odds API",
                "Clave de the-odds-api.com (capa gratuita). Déjalo vacío para no cambiarla.",
                secret=True),
    SettingSpec("player_sources", "str", "Plantillas",
                "Fuentes de plantillas",
                "Lista separada por comas: thesportsdb,wikipedia,wikidata,apifootball,sportmonks,fixture."),
    SettingSpec("enable_availability_adjustment", "bool", "Modelo y simulación",
                "Ajuste por disponibilidad",
                "Ajusta la fuerza del equipo según bajas/lesiones/sanciones."),
    SettingSpec("availability_adj_strength", "float", "Modelo y simulación",
                "Fuerza del ajuste",
                "Cuánto pesan las bajas en la fuerza efectiva (0–1).",
                min=0.0, max=1.0),
    SettingSpec("simulation_iterations", "int", "Modelo y simulación",
                "Iteraciones Monte Carlo",
                "Más iteraciones = menos varianza en el % de campeón (más lento).",
                min=1000, max=50000),
    SettingSpec("notifications_enabled", "bool", "Notificaciones",
                "Emails a suscriptores",
                "Envía el digest diario por email (requiere SMTP configurado)."),
    SettingSpec("sync_hour_utc", "int", "Refresco diario",
                "Hora del refresco (UTC)",
                "Hora UTC del refresco diario + digest (aplica tras reiniciar).",
                min=0, max=23),
    SettingSpec("affiliate_enabled", "bool", "Monetización",
                "CTA de afiliado activo",
                "Muestra el botón de afiliado (p. ej. casa de apuestas) en la web."),
    SettingSpec("affiliate_url", "str", "Monetización",
                "URL de afiliado",
                "Tu enlace con el tag de afiliación. Se abre en pestaña nueva."),
    SettingSpec("affiliate_label", "str", "Monetización",
                "Nombre a mostrar",
                "Texto del botón, p. ej. el nombre de la casa (Bet365, Codere…)."),
    SettingSpec("growth_agent_enabled", "bool", "Crecimiento",
                "Agente de crecimiento activo",
                "Cron que genera ideas de promoción/SEO/contenido y te las envía por email."),
    SettingSpec("growth_agent_minutes", "int", "Crecimiento",
                "Cada cuántos minutos",
                "Frecuencia del ciclo del agente (aplica del todo tras reiniciar).",
                min=30, max=720),
    SettingSpec("deepseek_api_key", "str", "Crecimiento",
                "API key de DeepSeek",
                "Clave de api.deepseek.com (OpenAI-compatible). Déjalo vacío para no cambiarla.",
                secret=True),
    SettingSpec("deepseek_model", "str", "Crecimiento",
                "Modelo de DeepSeek",
                "Modelo a usar, p. ej. deepseek-chat."),
    SettingSpec("growth_report_email", "str", "Crecimiento",
                "Email del informe",
                "Dirección a la que llega el digest del agente de crecimiento."),
    SettingSpec("indexnow_key", "str", "Crecimiento",
                "Clave de IndexNow",
                "Clave para avisar a los buscadores de URLs nuevas. Vacío = sin ping.",
                secret=True),
)

_SPECS = {s.key: s for s in EDITABLE}


def _coerce(spec: SettingSpec, raw: object):
    if spec.type == "bool":
        value = str(raw).strip().lower() in ("1", "true", "yes", "on")
    elif spec.type == "int":
        value = int(float(raw))  # acepta "60" o "60.0"
    elif spec.type == "float":
        value = float(raw)
    else:
        return str(raw)
    if spec.min is not None:
        value = max(spec.min if spec.type == "float" else int(spec.min), value)
    if spec.max is not None:
        value = min(spec.max if spec.type == "float" else int(spec.max), value)
    return value


def _to_text(spec: SettingSpec, value: object) -> str:
    if spec.type == "bool":
        return "true" if value else "false"
    return str(value)


async def apply_overrides(db: AsyncSession) -> None:
    """Carga los overrides de la DB y los aplica sobre el `settings` en memoria."""
    rows = (await db.execute(select(AppSetting))).scalars().all()
    overrides = {r.key: r.value for r in rows if r.value is not None}
    for spec in EDITABLE:
        if spec.key in overrides:
            try:
                object.__setattr__(settings, spec.key, _coerce(spec, overrides[spec.key]))
            except (ValueError, TypeError):
                logger.warning("Override inválido para %s=%r (se ignora).", spec.key, overrides[spec.key])


async def save_overrides(db: AsyncSession, values: dict[str, object]) -> None:
    """Valida y persiste los ajustes recibidos del panel; luego los aplica."""
    existing = {r.key: r for r in (await db.execute(select(AppSetting))).scalars().all()}
    for key, raw in values.items():
        spec = _SPECS.get(key)
        if spec is None:
            continue
        # Para secretos, un valor vacío significa "no cambiar".
        if spec.secret and (raw is None or str(raw).strip() == ""):
            continue
        text_val = _to_text(spec, _coerce(spec, raw))
        row = existing.get(key)
        if row is None:
            db.add(AppSetting(key=key, value=text_val))
        else:
            row.value = text_val
    await db.commit()
    await apply_overrides(db)


def effective_config() -> list[dict]:
    """Valores efectivos actuales (para el panel). Los secretos no se exponen."""
    out: list[dict] = []
    for spec in EDITABLE:
        item = {
            "key": spec.key,
            "type": spec.type,
            "group": spec.group,
            "label": spec.label,
            "desc": spec.desc,
            "secret": spec.secret,
            "min": spec.min,
            "max": spec.max,
        }
        value = getattr(settings, spec.key, None)
        if spec.secret:
            item["value"] = ""
            item["is_set"] = bool(value)
        else:
            item["value"] = value
        out.append(item)
    return out
