from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TeamSimulationRead(BaseModel):
    team_code: str
    team_name: str
    advance_prob: float
    round16_prob: float
    quarter_prob: float
    semi_prob: float
    final_prob: float
    champion_prob: float


class SimulationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    model_version: str
    iterations: int
    created_at: datetime
    teams: list[TeamSimulationRead]
