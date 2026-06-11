"""Router principal de la API v1: agrega todos los sub-routers."""

from fastapi import APIRouter

from app.api.endpoints import (
    admin,
    config,
    matches,
    predictions,
    simulate,
    squads,
    subscribers,
    sync,
    teams,
    venues,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(admin.auth_router)
api_router.include_router(admin.router)
api_router.include_router(teams.router)
api_router.include_router(matches.router)
api_router.include_router(predictions.router)
api_router.include_router(sync.router)
api_router.include_router(squads.router)
api_router.include_router(simulate.router)
api_router.include_router(subscribers.router)
api_router.include_router(venues.router)
api_router.include_router(config.router)
