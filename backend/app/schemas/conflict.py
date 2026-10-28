"""Conflict listing and resolution schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConflictResolveIn(BaseModel):
    """Payload for human consensus resolution of a conflict."""

    decision: Literal["include", "exclude", "maybe"]
    reviewer: str = Field(..., min_length=1, description="Panel or reviewer resolving the conflict")
    note: str | None = Field(default=None, description="Consensus notes")
    criterion_id: str | None = None
    reason_text: str | None = None

    @model_validator(mode="after")
    def validate_exclusion_reason(self) -> ConflictResolveIn:
        if self.decision == "exclude":
            has_crit = bool(self.criterion_id and self.criterion_id.strip())
            has_reason = bool(self.reason_text and self.reason_text.strip())
            if not (has_crit or has_reason):
                raise ValueError(
                    "An exclusion resolution requires either a criterion_id or reason_text."
                )
        return self


class ConflictResponse(BaseModel):
    """Conflict details."""

    id: str
    review_id: str
    group_id: str
    reason: str
    status: str
    open_fingerprint: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConflictResolveResult(BaseModel):
    """Result of conflict resolution."""

    status: str = "resolved"
    conflict_id: str
    affected_records_count: int
