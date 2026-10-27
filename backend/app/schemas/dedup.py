"""Deduplication and Duplicate Pair Pydantic schemas."""

from datetime import datetime

from backend.app.schemas.contracts import DuplicateDecisionType
from pydantic import BaseModel, ConfigDict, Field


class RecordSummary(BaseModel):
    id: str
    review_id: str
    source: str
    source_record_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    pmid: str | None = None
    model_config = ConfigDict(from_attributes=True)


class PairDecisionIn(BaseModel):
    record_a_id: str | None = None
    record_b_id: str | None = None
    duplicate_pair_id: str | None = None
    decision: DuplicateDecisionType
    reviewer_name: str = Field(default="Reviewer", description="Name of reviewer making verdict")
    note: str | None = None


class PairDecisionResponse(BaseModel):
    id: str
    duplicate_pair_id: str
    decision: str
    reviewer_name: str
    note: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DuplicatePairResponse(BaseModel):
    id: str
    review_id: str
    record_a_id: str
    record_b_id: str
    record_a: RecordSummary | None = None
    record_b: RecordSummary | None = None
    similarity_score: float
    tier: str
    match_reasons: list[str] = Field(default_factory=list)
    status: str
    created_at: datetime
    decisions: list[PairDecisionResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class PairDecisionResult(BaseModel):
    status: str = "recorded"
    decision_id: str
    duplicate_pair_id: str
    affected_group_id: str | None = None
