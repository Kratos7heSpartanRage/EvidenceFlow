"""Screening decision request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScreeningDecisionIn(BaseModel):
    """Payload for submitting a human screening decision.

    Non-negotiable invariant: Every exclusion must have an explicit reason
    (either criterion_id or non-empty reason_text).
    """

    decision: Literal["include", "exclude", "maybe"]
    criterion_id: str | None = None
    reason_text: str | None = None
    reviewer_name: str = Field(..., min_length=1, description="Name or identifier of the reviewer")
    note: str | None = None

    @model_validator(mode="after")
    def validate_exclusion_reason(self) -> ScreeningDecisionIn:
        if self.decision == "exclude":
            has_crit = bool(self.criterion_id and self.criterion_id.strip())
            has_reason = bool(self.reason_text and self.reason_text.strip())
            if not (has_crit or has_reason):
                raise ValueError(
                    "An exclusion decision strictly requires either a criterion_id or reason_text."
                )
        return self


class ScreeningDecisionResponse(BaseModel):
    """Full detail of a recorded screening decision."""

    id: str
    record_id: str
    group_id: str | None = None
    decision: str
    criterion_id: str | None = None
    reason_text: str | None = None
    reviewer_name: str
    origin: str
    note: str | None = None
    superseded_by_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
