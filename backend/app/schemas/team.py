from pydantic import BaseModel, ConfigDict


class TeamBase(BaseModel):
    name: str
    code: str
    confederation: str | None = None
    group: str | None = None
    fifa_rank: int | None = None


class TeamCreate(TeamBase):
    pass


class TeamRead(TeamBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
