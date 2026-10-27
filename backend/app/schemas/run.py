"""Pipeline Run and Step Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RunStepResponse(BaseModel):
    id: str
    run_id: str
    step_order: int
    name: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str | None = None
    model_config = ConfigDict(from_attributes=True)


class PipelineRunResponse(BaseModel):
    id: str
    review_id: str
    query_version_id: str | None = None
    run_type: str
    status: str
    progress_percent: int
    current_step: str | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[RunStepResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
