"""Pipeline del agente de crecimiento.

Cada ciclo (`run_growth_cycle`):
1. recarga overrides de configuración,
2. si falta la API key de DeepSeek → registra el run en error y avisa al dueño por
   email (no crashea),
3. reúne contexto del sitio (datos + monetización + historial de ideas previas),
4. pide a DeepSeek un JSON con ideas nuevas (las de monetización SIEMPRE requieren
   aprobación: no se ejecutan solas),
5. guarda cada idea como `GrowthInsight` (con dedup contra ideas recientes),
6. ejecuta acciones automáticas seguras (ping a IndexNow),
7. envía un digest por email al dueño y cierra el `GrowthRun`.

Todo va envuelto en try/except: un fallo marca el run como error y no rompe el
scheduler ni el proceso.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.growth import GrowthInsight, GrowthRun
from app.models.match import Match, MatchStatus
from app.models.simulation import SimulationResult, SimulationRun
from app.models.team import Team
from app.services.app_settings import apply_overrides
from app.services.growth import deepseek
from app.services.growth.indexnow import ping_indexnow
from app.services.notifications import send_growth_report

logger = logging.getLogger("maya.growth")

_VALID_CATEGORIES = {"seo", "promotion", "content", "monetization", "technical"}
_VALID_ACTIONS = {
    "email_only",
    "social_post",
    "seo_suggestion",
    "auto_sitemap",
    "indexnow",
}


def _normalize_title(title: str) -> str:
    """Normaliza un título para deduplicar (minúsculas, sin puntuación ni dobles espacios)."""
    cleaned = re.sub(r"[^\w\s]", " ", title.lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


async def _gather_context(db: AsyncSession) -> dict:
    """Reúne el estado del sitio + el historial de ideas, para alimentar el prompt."""
    n_teams = (await db.execute(select(func.count()).select_from(Team))).scalar_one()
    n_matches = (await db.execute(select(func.count()).select_from(Match))).scalar_one()

    teams = {t.id: t.name for t in (await db.execute(select(Team))).scalars().all()}
    upcoming = (
        (
            await db.execute(
                select(Match)
                .where(Match.status == MatchStatus.SCHEDULED, Match.home_team_id.is_not(None))
                .order_by(Match.kickoff)
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    def _name(tid: int | None) -> str:
        return teams.get(tid, "?") if tid else "?"

    next_matches = [
        {
            "home": _name(m.home_team_id),
            "away": _name(m.away_team_id),
            "kickoff": m.kickoff.isoformat() if m.kickoff else None,
        }
        for m in upcoming
    ]

    favorite: str | None = None
    run = (
        await db.execute(select(SimulationRun).order_by(desc(SimulationRun.created_at)).limit(1))
    ).scalar_one_or_none()
    if run is not None:
        row = (
            await db.execute(
                select(Team.name)
                .join(SimulationResult, SimulationResult.team_id == Team.id)
                .where(SimulationResult.run_id == run.id)
                .order_by(desc(SimulationResult.champion_prob))
                .limit(1)
            )
        ).scalar_one_or_none()
        favorite = row

    previous = (await db.execute(select(GrowthInsight).order_by(desc(GrowthInsight.id)).limit(15))).scalars().all()
    history = [{"title": i.title, "category": i.category, "status": i.status} for i in previous]

    return {
        "teams": n_teams,
        "matches": n_matches,
        "next_matches": next_matches,
        "favorite": favorite,
        "monetization": {
            "affiliate_enabled": settings.affiliate_enabled,
            "ads_configured": bool(settings.affiliate_url),
        },
        "history": history,
    }


def _build_messages(context: dict) -> list[dict]:
    system = (
        "Eres un estratega senior de growth marketing y SEO para 'mayapredice.site', "
        "una web en español que predice los resultados del Mundial de Fútbol 2026 con un "
        "modelo estadístico (Dixon-Coles). Está monetizada con Google AdSense y enlaces de "
        "afiliados (casas de apuestas, con avisos +18). Tu objetivo: hacer crecer el tráfico "
        "orgánico y social y aumentar los ingresos de forma ética.\n\n"
        "Devuelve EXCLUSIVAMENTE un objeto JSON con esta forma:\n"
        '{"insights": [{"category": "...", "title": "...", "body": "...", '
        '"priority": 1, "requires_approval": false, "action_type": "...", "content": "..."}]}\n\n'
        "Reglas:\n"
        "- category ∈ {seo, promotion, content, monetization, technical}.\n"
        "- priority entero 1 (alta) a 5 (baja).\n"
        "- action_type ∈ {email_only, social_post, seo_suggestion, auto_sitemap, indexnow}.\n"
        "- 'content' (opcional) es texto LISTO para publicar: un post de redes, lista de "
        "keywords SEO, o una meta-descripción.\n"
        "- Las ideas de category 'monetization' SIEMPRE deben llevar requires_approval=true "
        "(no se ejecutan automáticamente).\n"
        "- Propón ideas NUEVAS y concretas, distintas a las del historial que te paso.\n"
        "- Entre 4 y 8 ideas. Todo en español."
    )
    user = (
        "Contexto actual del sitio (JSON):\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n\nGenera nuevas ideas de crecimiento construyendo sobre el historial sin repetirlo."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_insights(raw: str) -> list[dict]:
    """Parsea defensivamente la respuesta del modelo a una lista de dicts de insight."""
    text = raw.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Intenta extraer el primer objeto JSON embebido.
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("insights") or data.get("ideas") or []
    else:
        items = []
    return [i for i in items if isinstance(i, dict)]


def _coerce_insight(item: dict) -> dict:
    """Normaliza un insight crudo del modelo a campos válidos del ORM."""
    category = str(item.get("category", "promotion")).strip().lower()
    if category not in _VALID_CATEGORIES:
        category = "promotion"
    action_type = str(item.get("action_type", "email_only")).strip().lower()
    if action_type not in _VALID_ACTIONS:
        action_type = "email_only"

    try:
        priority = int(item.get("priority", 3))
    except (TypeError, ValueError):
        priority = 3
    priority = max(1, min(5, priority))

    requires_approval = bool(item.get("requires_approval", False))
    # Regla dura: la monetización nunca se ejecuta sola.
    if category == "monetization":
        requires_approval = True

    title = str(item.get("title", "")).strip()[:200]
    body = item.get("body")
    content = item.get("content")
    payload = {"content": content} if content else None

    return {
        "category": category,
        "title": title,
        "body": str(body) if body is not None else None,
        "priority": priority,
        "requires_approval": requires_approval,
        "action_type": action_type,
        "payload": payload,
    }


async def _recent_titles(db: AsyncSession, limit: int = 30) -> set[str]:
    rows = (await db.execute(select(GrowthInsight.title).order_by(desc(GrowthInsight.id)).limit(limit))).scalars().all()
    return {_normalize_title(t) for t in rows}


def _esc(text: object) -> str:
    s = "" if text is None else str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _digest_html(
    sections: dict[str, list[GrowthInsight]],
    auto_done: list[str],
    config_pending: str | None,
) -> str:
    def block(title: str, insights: list[GrowthInsight]) -> str:
        if not insights:
            return ""
        rows = ""
        for i in insights:
            content = ""
            if i.payload and i.payload.get("content"):
                content = (
                    '<div style="margin-top:6px;padding:8px;background:#f1f5f9;border-radius:8px;'
                    f'white-space:pre-wrap;font-size:13px">{_esc(i.payload["content"])}</div>'
                )
            rows += (
                '<li style="margin:0 0 14px">'
                f"<strong>{_esc(i.title)}</strong> "
                f'<span style="color:#64748b">(prioridad {i.priority} · {_esc(i.category)})</span>'
                f'<div style="color:#334155;font-size:14px">{_esc(i.body)}</div>'
                f"{content}</li>"
            )
        return (
            f'<h3 style="font-family:sans-serif;color:#0f172a;margin:24px 0 8px">{title}</h3>'
            f'<ul style="font-family:sans-serif;padding-left:18px;margin:0">{rows}</ul>'
        )

    auto_block = ""
    if auto_done:
        items = "".join(f"<li>{_esc(a)}</li>" for a in auto_done)
        auto_block = (
            '<h3 style="font-family:sans-serif;color:#0f172a;margin:24px 0 8px">'
            "Acciones automáticas hechas</h3>"
            f'<ul style="font-family:sans-serif;padding-left:18px;margin:0">{items}</ul>'
        )

    config_block = ""
    if config_pending:
        config_block = (
            '<div style="margin:24px 0;padding:14px;background:#fef3c7;border-radius:10px;'
            'font-family:sans-serif;color:#92400e">'
            f"<strong>Configuración pendiente:</strong> {_esc(config_pending)}</div>"
        )

    return f"""\
<div style="max-width:640px;margin:0 auto;font-family:sans-serif;color:#0f172a">
  <div style="background:linear-gradient(135deg,#2dd4bf,#a78bfa);padding:24px;border-radius:14px;color:#04241d">
    <h1 style="margin:0;font-size:20px">📈 Agente de crecimiento · maya-predice</h1>
    <p style="margin:6px 0 0">Ideas para hacer crecer mayapredice.site, listas para revisar.</p>
  </div>
  {config_block}
  {block("Ideas de promoción nuevas", sections.get("promotion", []))}
  {block("Contenido listo para publicar", sections.get("content", []))}
  {auto_block}
  {block("Propuestas de MONETIZACIÓN (requieren tu aprobación)", sections.get("monetization", []))}
  <p style="color:#94a3b8;font-size:12px;text-align:center;margin-top:28px">
    Generado automáticamente por el agente de crecimiento de maya-predice.
  </p>
</div>"""


async def run_growth_cycle(db: AsyncSession, *, trigger: str = "growth") -> dict:
    """Ejecuta un ciclo del agente de crecimiento. Devuelve un resumen (dict)."""
    await apply_overrides(db)

    run = GrowthRun(status="running", trigger=trigger, model=settings.deepseek_model)
    db.add(run)
    await db.flush()

    # Falta la API key: registra el run en error y avisa al dueño por email.
    if not settings.deepseek_api_key:
        msg = (
            "El agente de crecimiento está activo pero falta configurar DEEPSEEK_API_KEY. "
            "Añádela en el panel de administración (⚙️ Configuración → Crecimiento) o como "
            "variable de entorno para que pueda generar ideas."
        )
        run.status = "error"
        run.summary = "Falta DEEPSEEK_API_KEY."
        run.error = msg
        run.finished_at = datetime.now(UTC)
        await db.commit()
        html = f'<div style="font-family:sans-serif"><h2>Configura DEEPSEEK_API_KEY</h2><p>{_esc(msg)}</p></div>'
        await send_growth_report("⚙️ maya-predice · configura DEEPSEEK_API_KEY", html, settings.growth_report_email)
        return {"status": "error", "reason": "deepseek_not_configured", "run_id": run.id}

    try:
        context = await _gather_context(db)
        messages = _build_messages(context)
        raw = await deepseek.chat(messages, model=settings.deepseek_model, response_json=True, max_tokens=2500)

        try:
            parsed = _parse_insights(raw)
        except json.JSONDecodeError as exc:
            run.status = "error"
            run.summary = "DeepSeek devolvió un JSON no parseable."
            run.error = f"{exc}: {raw[:500]}"
            run.finished_at = datetime.now(UTC)
            await db.commit()
            return {"status": "error", "reason": "bad_json", "run_id": run.id}

        recent = await _recent_titles(db)
        created: list[GrowthInsight] = []
        for item in parsed:
            data = _coerce_insight(item)
            if not data["title"]:
                continue
            norm = _normalize_title(data["title"])
            if norm in recent:
                continue
            recent.add(norm)
            insight = GrowthInsight(run_id=run.id, status="new", **data)
            db.add(insight)
            created.append(insight)
        await db.flush()

        # --- Acciones automáticas seguras (nunca monetización) ---
        auto_done: list[str] = []
        site = settings.public_site_url.rstrip("/")
        urls = [site, f"{site}/fixture", f"{site}/equipos", f"{site}/simulacion"]
        if settings.indexnow_key:
            ok = await ping_indexnow(urls)
            if ok:
                idx = GrowthInsight(
                    run_id=run.id,
                    category="seo",
                    title="Ping a IndexNow de las URLs principales",
                    body="Se notificó a los buscadores (IndexNow) que las páginas principales "
                    "están disponibles para acelerar su rastreo.",
                    priority=3,
                    status="done",
                    requires_approval=False,
                    action_type="indexnow",
                    payload={"urls": urls},
                )
                db.add(idx)
                created.append(idx)
                auto_done.append(f"IndexNow notificado de {len(urls)} URLs.")
        await db.flush()

        # --- Digest por email ---
        sections: dict[str, list[GrowthInsight]] = {
            "promotion": [],
            "content": [],
            "monetization": [],
        }
        emailable: list[GrowthInsight] = []
        for i in created:
            if i.status == "done":
                continue
            emailable.append(i)
            if i.category == "monetization":
                sections["monetization"].append(i)
            elif i.category == "content":
                sections["content"].append(i)
            else:
                sections["promotion"].append(i)

        html = _digest_html(sections, auto_done, None)
        sent = await send_growth_report(
            "📈 maya-predice · nuevas ideas de crecimiento", html, settings.growth_report_email
        )
        if sent:
            for i in emailable:
                i.status = "emailed"

        run.status = "done"
        run.insights_count = len(created)
        run.finished_at = datetime.now(UTC)
        run.summary = (
            f"{len(created)} ideas ({len(sections['monetization'])} de monetización), "
            f"{len(auto_done)} acciones automáticas; email {'enviado' if sent else 'no enviado'}."
        )
        await db.commit()
        return {
            "status": "done",
            "run_id": run.id,
            "insights": len(created),
            "auto_actions": len(auto_done),
            "emailed": sent,
        }

    except deepseek.DeepSeekError as exc:
        run.status = "error"
        run.summary = "Fallo al consultar DeepSeek."
        run.error = str(exc)[:1000]
        run.finished_at = datetime.now(UTC)
        await db.commit()
        return {"status": "error", "reason": "deepseek_error", "run_id": run.id}
    except Exception as exc:  # noqa: BLE001 — el agente no debe romper el scheduler
        logger.exception("El ciclo de crecimiento falló.")
        try:
            run.status = "error"
            run.summary = "Error inesperado en el ciclo de crecimiento."
            run.error = str(exc)[:1000]
            run.finished_at = datetime.now(UTC)
            await db.commit()
        except Exception:  # noqa: BLE001
            await db.rollback()
        return {"status": "error", "reason": "exception", "run_id": run.id}
