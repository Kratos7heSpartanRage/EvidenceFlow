"""Deduplication and Duplicate Pair Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.contracts import DuplicateDecisionType


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

    @field_validator("authors", mode="before")
    @classmethod
    def author_names(cls, values):
        return [item.get("full_name", "") if isinstance(item, dict) else item for item in values]


class PairDecisionIn(BaseModel):
    record_a_id: str | None = None
    record_b_id: str | None = None
    duplicate_pair_id: str | None = None
    decision: DuplicateDecisionType
    reviewer_name: str = Field(default="Reviewer", description="Name of reviewer making verdict")
    note: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        if self.duplicate_pair_id:
            if self.record_a_id is not None or self.record_b_id is not None:
                raise ValueError("Supply a pair id or two record ids, not both.")
        elif not self.record_a_id or not self.record_b_id or self.record_a_id == self.record_b_id:
            raise ValueError("Supply a pair id or two distinct record ids.")
        if not self.reviewer_name.strip():
            raise ValueError("Reviewer name cannot be blank.")
        return self


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
