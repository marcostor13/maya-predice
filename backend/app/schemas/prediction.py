from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScorelineProb(BaseModel):
    home: int
    away: int
    prob: float


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    model_version: str
    p_home: float
    p_draw: float
    p_away: float
    expected_home_goals: float
    expected_away_goals: float
    scoreline_probs: list[ScorelineProb] | None = None
    adjustments: dict | None = None
    ensemble: dict | None = None
    created_at: datetime


class RunPredictionRequest(BaseModel):
    """Solicita ejecutar el modelo. Si match_id se da, predice ese partido;
    si se dan home/away (códigos), predice un enfrentamiento ad-hoc."""

    match_id: int | None = None
    home: str | None = None
    away: str | None = None


class TeamSimResult(BaseModel):
    code: str
    advance_prob: float
    champion_prob: float
