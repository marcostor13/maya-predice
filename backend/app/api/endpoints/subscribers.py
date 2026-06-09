from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
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


def _page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · maya-predice</title></head>
<body style="margin:0;font-family:sans-serif;background:#0a0e1a;color:#eef2ff;
display:grid;place-items:center;min-height:100vh">
<div style="max-width:440px;text-align:center;padding:36px;background:rgba(255,255,255,.05);
border:1px solid rgba(255,255,255,.1);border-radius:16px">
<div style="font-size:3rem">⚽</div>
<h1 style="font-family:sans-serif">{title}</h1>
<p style="color:#9aa6c9">{body}</p></div></body></html>"""


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe(token: str, db: AsyncSession = Depends(get_db)):
    """Da de baja a un suscriptor mediante su token (enlace del email)."""
    sub = (
        await db.execute(select(Subscriber).where(Subscriber.token == token))
    ).scalar_one_or_none()
    if sub is None:
        return HTMLResponse(
            _page("Enlace no válido", "No encontramos esa suscripción. Quizá ya te diste de baja."),
            status_code=404,
        )
    sub.active = False
    return HTMLResponse(
        _page("Te has dado de baja", "Ya no recibirás más correos. Puedes volver a suscribirte cuando quieras.")
    )
