"""Envío de novedades y predicciones por email a los suscriptores.

Compone un *digest* HTML (resultados recientes, favoritos al título y próximos
partidos con su pronóstico) y lo envía por SMTP a los suscriptores activos. Se
dispara tras el refresco diario cuando hay resultados nuevos.

Requiere configurar SMTP en el entorno (`SMTP_*` + `NOTIFICATIONS_ENABLED=true`).
Si no está configurado, no envía (degradación silenciosa).
"""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.simulation import SimulationResult, SimulationRun
from app.models.subscriber import Subscriber
from app.models.team import Team

logger = logging.getLogger("maya.notifications")


def _row(left: str, mid: str, right: str) -> str:
    return (
        '<tr>'
        f'<td style="padding:10px 8px;font-weight:600;color:#0f172a">{left}</td>'
        f'<td style="padding:10px 8px;text-align:center;color:#0d9488;font-weight:700">{mid}</td>'
        f'<td style="padding:10px 8px;text-align:right;font-weight:600;color:#0f172a">{right}</td>'
        '</tr>'
    )


async def build_digest_html(db: AsyncSession) -> tuple[str, bool]:
    """Construye el HTML del digest. Devuelve (html, has_results)."""
    teams = {t.id: t for t in (await db.execute(select(Team))).scalars().all()}

    finished = (
        await db.execute(
            select(Match)
            .where(Match.status == MatchStatus.FINISHED)
            .order_by(desc(Match.kickoff))
            .limit(6)
        )
    ).scalars().all()

    upcoming = (
        await db.execute(
            select(Match)
            .where(Match.status == MatchStatus.SCHEDULED, Match.home_team_id.is_not(None))
            .order_by(Match.kickoff)
            .limit(6)
        )
    ).scalars().all()
    preds = {
        p.match_id: p
        for p in (
            await db.execute(select(Prediction).distinct(Prediction.match_id).order_by(
                Prediction.match_id, desc(Prediction.created_at)
            ))
        ).scalars().all()
    }

    run = (
        await db.execute(select(SimulationRun).order_by(desc(SimulationRun.created_at)).limit(1))
    ).scalar_one_or_none()
    contenders = []
    if run is not None:
        contenders = (
            await db.execute(
                select(SimulationResult, Team)
                .join(Team, Team.id == SimulationResult.team_id)
                .where(SimulationResult.run_id == run.id)
                .order_by(desc(SimulationResult.champion_prob))
                .limit(5)
            )
        ).all()

    def name(tid: int | None) -> str:
        return teams[tid].name if tid and tid in teams else "?"

    results_rows = "".join(
        _row(name(m.home_team_id), f"{m.home_goals} - {m.away_goals}", name(m.away_team_id))
        for m in finished
    )
    contenders_rows = "".join(
        _row(t.name, f"{r.champion_prob * 100:.1f}% campeón", "🏆") for r, t in contenders
    )
    upcoming_rows = ""
    for m in upcoming:
        p = preds.get(m.id)
        odds = (
            f"{p.p_home*100:.0f}% / {p.p_draw*100:.0f}% / {p.p_away*100:.0f}%"
            if p else "—"
        )
        upcoming_rows += _row(name(m.home_team_id), odds, name(m.away_team_id))

    def section(title: str, rows: str) -> str:
        if not rows:
            return ""
        return (
            f'<h3 style="font-family:sans-serif;color:#0f172a;margin:26px 0 6px">{title}</h3>'
            '<table style="width:100%;border-collapse:collapse;background:#f8fafc;'
            'border-radius:10px;font-family:sans-serif;font-size:14px">'
            f"{rows}</table>"
        )

    html = f"""\
<div style="max-width:600px;margin:0 auto;font-family:sans-serif;color:#0f172a">
  <div style="background:linear-gradient(135deg,#2dd4bf,#a78bfa);padding:28px;border-radius:14px;color:#04241d">
    <h1 style="margin:0;font-size:22px">⚽ maya-predice · Mundial 2026</h1>
    <p style="margin:6px 0 0">Tus predicciones y novedades, actualizadas tras la jornada.</p>
  </div>
  {section("🏁 Resultados recientes", results_rows)}
  {section("🔥 Favoritos al título", contenders_rows)}
  {section("📅 Próximos partidos (local / empate / visitante)", upcoming_rows)}
  <div style="text-align:center;margin:30px 0">
    <a href="{settings.site_url}" style="background:#2dd4bf;color:#04241d;text-decoration:none;
       font-weight:700;padding:12px 24px;border-radius:999px;font-family:sans-serif">
       Ver todo en la web →</a>
  </div>
  <p style="color:#94a3b8;font-size:12px;text-align:center;font-family:sans-serif">
    Recibes este correo porque te suscribiste en maya-predice.<br>
    Desarrollado por Marcos Torres · {settings.site_url}<br>
    <a href="__UNSUB__" style="color:#94a3b8">Darme de baja</a>
  </p>
</div>"""
    return html, bool(finished)


def _unsubscribe_url(token: str) -> str:
    return f"{settings.api_public_url.rstrip('/')}/subscribers/unsubscribe/{token}"


async def send_digest(
    subject: str, html_template: str, subscribers: list[Subscriber]
) -> int:
    """Envía el digest a cada suscriptor con su enlace de baja personalizado.

    Un email por destinatario (necesario para el unsubscribe individual), todos
    por la misma conexión SMTP. Incluye la cabecera `List-Unsubscribe`.
    """
    if not subscribers:
        return 0
    if not (settings.smtp_host and settings.smtp_from):
        logger.warning("SMTP no configurado; no se envía el email.")
        return 0

    smtp = aiosmtplib.SMTP(
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        start_tls=settings.smtp_start_tls,
        use_tls=settings.smtp_use_tls,
    )
    await smtp.connect()
    if settings.smtp_user:
        await smtp.login(settings.smtp_user, settings.smtp_password)

    sent = 0
    try:
        for sub in subscribers:
            unsub = _unsubscribe_url(sub.token)
            html = html_template.replace("__UNSUB__", unsub)
            msg = EmailMessage()
            msg["From"] = settings.smtp_from
            msg["To"] = sub.email
            msg["Subject"] = subject
            msg["List-Unsubscribe"] = f"<{unsub}>"
            msg.set_content("Activa el HTML para ver el contenido.")
            msg.add_alternative(html, subtype="html")
            try:
                await smtp.send_message(msg)
                sent += 1
            except aiosmtplib.SMTPException as exc:
                logger.warning("No se pudo enviar a %s: %s", sub.email, exc)
    finally:
        await smtp.quit()

    logger.info("Email enviado a %s suscriptores.", sent)
    return sent


async def notify_subscribers(db: AsyncSession, *, only_with_results: bool = True) -> int:
    """Compone el digest y lo envía a los suscriptores activos."""
    if not settings.notifications_enabled:
        logger.info("Notificaciones desactivadas (NOTIFICATIONS_ENABLED=false).")
        return 0

    subscribers = list(
        (await db.execute(select(Subscriber).where(Subscriber.active.is_(True)))).scalars()
    )
    if not subscribers:
        return 0

    html, has_results = await build_digest_html(db)
    if only_with_results and not has_results:
        logger.info("Sin resultados nuevos; no se envía digest.")
        return 0

    return await send_digest("⚽ maya-predice · Predicciones del Mundial 2026", html, subscribers)
