"""Punto de entrada de la API FastAPI de maya-predice."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.services.app_settings import apply_overrides

logger = logging.getLogger("maya.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aplica los overrides de configuración guardados (panel admin) sobre el entorno.
    async with AsyncSessionLocal() as db:
        try:
            await apply_overrides(db)
        except Exception:  # noqa: BLE001 — si la tabla aún no existe, se arranca igual
            logger.warning("No se pudieron aplicar los overrides de configuración al arrancar.")
    # Arranca los jobs programados (diario, aprendizaje horario, en vivo).
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="maya-predice API",
    description="Predicción estadística de los partidos del Mundial 2026 (Dixon-Coles).",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)

# CORS: "*" permite cualquier origen (API pública). Con orígenes explícitos se
# habilitan credenciales; con "*" el navegador exige allow_credentials=False.
_origins = settings.cors_origins_list
_allow_all = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env, "model_version": settings.model_version}
