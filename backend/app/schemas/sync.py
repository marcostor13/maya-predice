from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.sync import SyncStatus


class DataChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int | None
    external_ref: str
    change_type: str
    field: str
    old_value: str | None
    new_value: str | None
    created_at: datetime


class SyncRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    status: SyncStatus
    trigger: str
    started_at: datetime
    finished_at: datetime | None
    matches_seen: int
    created: int
    updated: int
    changes_count: int
    message: str | None
