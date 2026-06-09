from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.match import Match
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionRead, RunPredictionRequest
from app.services.prediction.training import persist_team_strengths
from app.services.prediction_service import predict_and_store, train_model

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/train")
async def train(db: AsyncSession = Depends(get_db)):
    """Reentrena el modelo con el histórico + resultados y persiste las fuerzas."""
    try:
        model = await train_model(db, force=True)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    saved = await persist_team_strengths(db, model)
    return {
        "teams": len(model.teams),
        "home_advantage": round(model.home_advantage, 4),
        "rho": round(model.rho, 4),
        "strengths_saved": saved,
    }


@router.get("", response_model=list[PredictionRead])
async def list_latest_predictions(db: AsyncSession = Depends(get_db)):
    """Última predicción de cada partido (una por match)."""
    stmt = (
        select(Prediction)
        .distinct(Prediction.match_id)
        .order_by(Prediction.match_id, desc(Prediction.created_at))
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/match/{match_id}", response_model=PredictionRead)
async def get_match_prediction(match_id: int, db: AsyncSession = Depends(get_db)):
    """Devuelve la predicción más reciente de un partido."""
    stmt = (
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(desc(Prediction.created_at))
        .limit(1)
    )
    prediction = (await db.execute(stmt)).scalar_one_or_none()
    if prediction is None:
        raise HTTPException(status_code=404, detail="Sin predicción para este partido")
    return prediction


@router.post("/run", response_model=PredictionRead)
async def run_prediction(payload: RunPredictionRequest, db: AsyncSession = Depends(get_db)):
    """Entrena el modelo y genera la predicción de un partido existente."""
    if payload.match_id is None:
        raise HTTPException(status_code=400, detail="match_id es obligatorio")

    match = await db.get(Match, payload.match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")

    try:
        model = await train_model(db)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        return await predict_and_store(db, match, model)
    except KeyError as exc:
        raise HTTPException(status_code=409, detail=f"Datos insuficientes: {exc}") from exc
