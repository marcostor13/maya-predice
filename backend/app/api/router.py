"""Router principal de la API v1: agrega todos los sub-routers."""

from fastapi import APIRouter

from app.api.endpoints import matches, predictions, sync, teams

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(teams.router)
api_router.include_router(matches.router)
api_router.include_router(predictions.router)
api_router.include_router(sync.router)
