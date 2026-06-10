from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.match import MatchStage, MatchStatus


class MatchBase(BaseModel):
    tournament_id: int
    home_team_id: int | None = None
    away_team_id: int | None = None
    stage: MatchStage = MatchStage.GROUP
    group: str | None = None
    matchday: int | None = None
    venue: str | None = None
    kickoff: datetime | None = None


class MatchCreate(MatchBase):
    external_ref: str


class VenueDetail(BaseModel):
    stadium: str
    city: str
    country: str
    capacity: int


class MatchRead(MatchBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    external_ref: str
    home_placeholder: str | None = None
    away_placeholder: str | None = None
    status: MatchStatus
    home_goals: int | None = None
    away_goals: int | None = None
    venue_detail: VenueDetail | None = None
