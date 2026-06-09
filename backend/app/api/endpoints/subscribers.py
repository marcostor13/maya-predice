from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.subscriber import Subscriber
from app.schemas.subscriber import SubscriberCreate

router = APIRouter(prefix="/subscribers", tags=["subscribers"])


@router.post("", status_code=201)
async def subscribe(payload: SubscriberCreate, db: AsyncSession = Depends(get_db)):
    """Alta de suscriptor (idempotente: reactiva si ya existía)."""
    email = payload.email.lower()
    existing = (
        await db.execute(select(Subscriber).where(Subscriber.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        existing.active = True
        return {"status": "ok", "message": "¡Ya estabas suscrito! Te mantendremos al día."}
    db.add(Subscriber(email=email))
    return {"status": "ok", "message": "¡Suscripción confirmada! Recibirás predicciones y novedades."}


@router.get("/count")
async def subscriber_count(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Subscriber))).scalar_one()
    return {"count": total}
