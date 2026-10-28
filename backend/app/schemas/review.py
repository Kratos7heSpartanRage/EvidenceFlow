"""Review and Criteria Pydantic schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CriterionIn(BaseModel):
    type: Literal["inclusion", "exclusion"] = Field(..., description="'inclusion' or 'exclusion'")
    label: str = Field(..., min_length=1, description="Short name of criterion")
    description: str = Field(
        ..., min_length=1, description="Detailed definition / eligibility reason"
    )
    field_target: str | None = Field(default=None, description="'title', 'abstract', 'mesh', etc.")
    detector_rule: str | None = Field(
        default=None, description="Named engine detector or literal keywords separated by |"
    )


class CriterionResponse(CriterionIn):
    id: str
    criteria_version_id: str
    model_config = ConfigDict(from_attributes=True)


class CriteriaVersionCreate(BaseModel):
    criteria: list[CriterionIn] = Field(..., description="Full array of criteria for new version")


class CriteriaVersionResponse(BaseModel):
    id: str
    review_id: str
    version_number: int
    created_at: datetime
    criteria: list[CriterionResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    question: str = Field(..., min_length=1, max_length=1000)
    pico: dict[str, Any] = Field(default_factory=dict, description="PICO framework dictionary")
    initial_criteria: list[CriterionIn] | None = Field(
        default=None, description="Optional initial criteria"
    )


class ReviewUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    question: str | None = Field(default=None, min_length=1, max_length=1000)
    pico: dict[str, Any] | None = None


class ReviewCounts(BaseModel):
    total_records: int = 0
    unique_studies: int = 0
    screened_included: int = 0
    screened_excluded: int = 0
    screened_maybe: int = 0
    unscreened: int = 0
    open_conflicts: int = 0


class ReviewResponse(BaseModel):
    id: str
    title: str
    question: str
    pico: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    counts: ReviewCounts = Field(default_factory=ReviewCounts)
    active_criteria_version: CriteriaVersionResponse | None = None
    active_query_id: str | None = None
    model_config = ConfigDict(from_attributes=True)


class ReviewListItem(BaseModel):
    id: str
    title: str
    question: str
    created_at: datetime
    updated_at: datetime
    counts: ReviewCounts = Field(default_factory=ReviewCounts)
    model_config = ConfigDict(from_attributes=True)
