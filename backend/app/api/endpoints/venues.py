from dataclasses import asdict

from fastapi import APIRouter

from app.data.venues import VENUES

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("")
async def list_venues():
    """Las 16 sedes del Mundial 2026 con estadio, ciudad, país y aforo."""
    return [{"key": key, **asdict(v)} for key, v in VENUES.items()]
