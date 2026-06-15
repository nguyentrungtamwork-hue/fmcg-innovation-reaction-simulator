from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    market: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str | None
    market: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectEnvelope(BaseModel):
    project: ProjectOut
    has_brief: bool
    has_ontology: bool
    agents_count: int
    events_count: int
    has_report: bool
