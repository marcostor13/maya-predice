"""Schemas (Pydantic) del agente de crecimiento para el panel admin."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GrowthInsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    created_at: datetime
    category: str
    title: str
    body: str | None = None
    priority: int
    status: str
    requires_approval: bool
    action_type: str
    payload: dict | None = None


class GrowthRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    model: str | None = None
    trigger: str
    summary: str | None = None
    error: str | None = None
    insights_count: int
    started_at: datetime
    finished_at: datetime | None = None
    insights: list[GrowthInsightRead] = []


class GrowthInsightUpdate(BaseModel):
    """Cambia el estado de un insight (aprobar/descartar)."""

    status: str
