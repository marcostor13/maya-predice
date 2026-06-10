from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.squad import PlayerStatus, Position, SquadRole


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    full_name: str
    position: Position
    shirt_number: int | None = None
    club: str | None = None
    birth_date: date | None = None
    role: SquadRole
    status: PlayerStatus
    photo_url: str | None = None
    info: str | None = None
    confidence: float
    sources_count: int
    source_data: dict | None = None
    updated_at: datetime


class CoachRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    name: str
    nationality: str | None = None
    status: PlayerStatus
    photo_url: str | None = None
    confidence: float
    sources_count: int
    source_data: dict | None = None
    updated_at: datetime


class SquadRead(BaseModel):
    team_code: str
    team_name: str
    coach: CoachRead | None = None
    players: list[PlayerRead]


class DiscrepancyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_code: str
    entity_type: str
    entity_name: str
    field: str
    chosen_value: str | None = None
    agreement: float
    by_source: dict | None = None
    created_at: datetime
