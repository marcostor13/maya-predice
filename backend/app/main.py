"""Punto de entrada de la API FastAPI de maya-predice."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranca el job diario de verificación de datos oficiales.
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="maya-predice API",
    description="Predicción estadística de los partidos del Mundial 2026 (Dixon-Coles).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env, "model_version": settings.model_version}
