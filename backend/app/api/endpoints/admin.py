"""Panel de administración: ejecuta las operaciones de mantenimiento por HTTP.

Autenticación con **login JWT**: `POST /admin/login` con usuario y contraseña
(guardados hasheados en `admin_users`, ver `python -m app.data.create_admin`)
devuelve un token; el resto de endpoints exigen `Authorization: Bearer <token>`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_token, verify_password
from app.models.admin_user import AdminUser
from app.models.cache import ApiCache
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.simulation import SimulationRun
from app.models.subscriber import Subscriber
from app.models.team import Team


def require_admin(authorization: str | None = Header(None)) -> None:
    if not (settings.jwt_secret or settings.admin_token):
        raise HTTPException(
            status_code=503, detail="Panel de admin deshabilitado: define JWT_SECRET (o ADMIN_TOKEN)."
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    if decode_token(authorization.split(" ", 1)[1]) is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")


class LoginRequest(BaseModel):
    username: str
    password: str


# Router de login (sin protección): emite el token.
auth_router = APIRouter(prefix="/admin", tags=["admin"])


@auth_router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not (settings.jwt_secret or settings.admin_token):
        raise HTTPException(status_code=503, detail="Auth no configurada: define JWT_SECRET o ADMIN_TOKEN.")
    user = (
        await db.execute(select(AdminUser).where(AdminUser.username == payload.username))
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    token = create_access_token(user.username, settings.jwt_expire_hours)
    return {"access_token": token, "token_type": "bearer", "username": user.username}


# Router protegido: requiere un JWT válido.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/check")
async def check():
    """Valida la sesión (lo usa el panel al cargar)."""
    return {"ok": True}


@router.get("/factors")
async def factors():
    """Qué tiene en cuenta el modelo para la predicción (con la config actual)."""
    return {
        "config": {
            "filtro_historico": settings.history_team_filter,
            "desde_anio": settings.history_since_year,
            "decaimiento_temporal_xi": settings.model_decay_xi,
            "peso_prior_elo": settings.elo_prior_weight,
            "ajuste_por_disponibilidad": settings.enable_availability_adjustment,
            "iteraciones_simulacion": settings.simulation_iterations,
            "fuentes_plantillas": settings.player_sources_list,
            "ensamble_mercado": settings.enable_market_ensemble,
            "peso_modelo_ensamble": settings.ensemble_model_weight,
        },
        "factores": [
            *(
                [{
                    "icon": "💰",
                    "nombre": "Cuotas de mercado (ensamble)",
                    "desc": "La predicción 1X2 se mezcla con la probabilidad implícita de las casas "
                            f"de apuestas (ω={settings.ensemble_model_weight} al modelo): es la señal "
                            "más precisa que existe, como hace el supercomputador de Opta.",
                }]
                if settings.enable_market_ensemble
                else []
            ),
            {"icon": "📊", "nombre": "Fuerza histórica (ataque y defensa)",
             "desc": "Estimada por máxima verosimilitud de ~49.000 partidos internacionales reales (martj42)."},
            {"icon": "🏅", "nombre": "Prior Elo",
             "desc": "Rating ajustado por rival y diferencia de goles que ancla la fuerza "
                     "(predice mejor que el ranking FIFA)."},
            {"icon": "⏱️", "nombre": "Forma reciente (decaimiento temporal)",
             "desc": "Los partidos recientes pesan más que los antiguos; el modelo mejora conforme llegan resultados."},
            {"icon": "🎖️", "nombre": "Importancia del partido",
             "desc": "Amistoso (0.5) < clasificatorio (1.0) < fase final (1.5): "
                     "los amistosos con rotaciones cuentan menos."},
            {"icon": "🏟️", "nombre": "Sede neutral",
             "desc": "En el Mundial casi todo es cancha neutral, así que no se aplica ventaja de localía."},
            {"icon": "🎯", "nombre": "Corrección Dixon-Coles (rho)",
             "desc": "Ajusta los marcadores bajos (0-0, 1-0, 1-1) que el Poisson puro no captura bien."},
            {"icon": "🩹", "nombre": "Disponibilidad de la plantilla",
             "desc": "Bajas, lesiones, sanciones y dudas reducen la fuerza efectiva según posición y rol."},
            {"icon": "🎲", "nombre": "Simulación Monte Carlo (sorteo aleatorio)",
             "desc": "Miles de torneos simulados con sorteo de cuadro aleatorio "
                     "(sin camino regalado) para avanzar/campeón."},
        ],
    }


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    """Conteos del estado actual de los datos."""

    async def count(model) -> int:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()

    finished = (
        await db.execute(
            select(func.count()).select_from(Match).where(Match.status == MatchStatus.FINISHED)
        )
    ).scalar_one()
    last_sim = (
        await db.execute(select(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    active_subs = (
        await db.execute(
            select(func.count()).select_from(Subscriber).where(Subscriber.active.is_(True))
        )
    ).scalar_one()
    return {
        "teams": await count(Team),
        "matches": await count(Match),
        "matches_finished": finished,
        "predictions": await count(Prediction),
        "subscribers_active": active_subs,
        "api_cache_rows": await count(ApiCache),
        "last_simulation": last_sim.created_at.isoformat() if last_sim else None,
        "model_version": settings.model_version,
    }


@router.post("/sync")
async def admin_sync(db: AsyncSession = Depends(get_db)):
    from app.services.sync_service import default_provider, sync_official_data

    run = await sync_official_data(db, default_provider(), trigger="admin")
    return {"ok": True, "message": run.message}


@router.post("/recompute")
async def admin_recompute(db: AsyncSession = Depends(get_db)):
    """Lanza el recálculo completo en **segundo plano** y responde al instante.

    El trabajo es pesado (reentreno + 5000 simulaciones); correrlo síncrono haría
    que la petición se quedara colgada y un refresco de la página la cortara. En su
    lugar se crea un `JobRun` y el panel consulta el estado con `GET /admin/job`.
    """
    from app.services.jobs import JobInProgress, job_to_dict, start_job
    from app.services.recompute import recompute_pipeline

    async def work(session):
        return await recompute_pipeline(session, trigger="admin", force=True)

    try:
        job = await start_job(db, "recompute", work)
    except JobInProgress as exc:
        # 409: ya hay uno en curso; el panel se engancha a su estado.
        return {"ok": True, "started": False, "job": job_to_dict(exc.job)}
    return {"ok": True, "started": True, "job": job_to_dict(job)}


@router.get("/job")
async def admin_job(db: AsyncSession = Depends(get_db)):
    """Estado del último recálculo (para el polling del panel): idle/running/done/error."""
    from app.services.jobs import job_to_dict, latest_job

    return job_to_dict(await latest_job(db, name="recompute"))


@router.post("/train")
async def admin_train(db: AsyncSession = Depends(get_db)):
    from app.services.prediction.training import persist_team_strengths, train_model

    model = await train_model(db, force=True)
    saved = await persist_team_strengths(db, model)
    return {
        "ok": True,
        "teams": len(model.teams),
        "home_advantage": round(model.home_advantage, 4),
        "rho": round(model.rho, 4),
        "strengths_saved": saved,
    }


@router.post("/simulate")
async def admin_simulate(db: AsyncSession = Depends(get_db)):
    from app.services.prediction_service import train_model
    from app.services.simulation_service import run_simulation

    model = await train_model(db)
    run = await run_simulation(db, model, trigger="admin")
    return {"ok": True, "iterations": run.iterations, "teams": getattr(run, "result_count", 0)}


@router.post("/squads")
async def admin_squads(db: AsyncSession = Depends(get_db)):
    from app.services.squad_service import build_player_providers, sync_squads

    providers = build_player_providers()
    if not providers:
        raise HTTPException(status_code=409, detail="No hay fuentes de plantillas configuradas (PLAYER_SOURCES).")
    run = await sync_squads(db, providers, trigger="admin")
    return {"ok": True, "sources": [p.name for p in providers], "message": run.message}


@router.post("/notify")
async def admin_notify(db: AsyncSession = Depends(get_db)):
    from app.services.notifications import notify_subscribers

    sent = await notify_subscribers(db, only_with_results=False)
    return {"ok": True, "sent": sent}


@router.post("/bootstrap")
async def admin_bootstrap():
    from app.data.bootstrap import run as bootstrap_run

    await bootstrap_run(force=True)
    return {"ok": True, "message": "Carga inicial ejecutada (partidos, modelo, predicciones, simulación, plantillas)."}


@router.get("/backtest")
async def admin_backtest():
    from app.services.prediction.backtest import run_backtest

    try:
        result = await run_backtest()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.to_dict()
