from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.match import MatchStage, MatchStatus


class MatchBase(BaseModel):
    tournament_id: int
    home_team_id: int
    away_team_id: int
    stage: MatchStage = MatchStage.GROUP
    group: str | None = None
    venue: str | None = None
    kickoff: datetime | None = None


class MatchCreate(MatchBase):
    pass


class MatchRead(MatchBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: MatchStatus
    home_goals: int | None = None
    away_goals: int | None = None
