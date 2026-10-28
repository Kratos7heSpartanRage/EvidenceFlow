"""Record Pydantic schemas for list and detail bibliographic representations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecordDecisionSummary(BaseModel):
    id: str
    decision: str
    criterion_id: str | None = None
    reason_text: str | None = None
    reviewer_name: str
    note: str | None = None
    origin: str = "human"
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RecordSuggestionSummary(BaseModel):
    id: str
    suggested_decision: str
    confidence: float
    matched_criterion_id: str | None = None
    matched_criterion_label: str | None = None
    algorithm_version: str | None = None
    model_config = ConfigDict(from_attributes=True)


class PicoSpanItem(BaseModel):
    id: str
    element: str
    text: str
    start_index: int | None = None
    end_index: int | None = None
    confidence: float | None = None
    origin: str
    is_confirmed: bool = False
    status: str | None = None
    model_config = ConfigDict(from_attributes=True)


class RecordItem(BaseModel):
    id: str
    review_id: str
    source: str
    source_record_id: str
    title: str
    authors: list[str | dict[str, Any]] = Field(default_factory=list)
    journal: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    pmid: str | None = None
    group_id: str | None = None
    is_representative: bool = True
    is_hidden: bool = False
    decision: RecordDecisionSummary | None = None
    suggestion: RecordSuggestionSummary | None = None
    model_config = ConfigDict(from_attributes=True)


class RecordListResponse(BaseModel):
    items: list[RecordItem]
    total: int
    page: int
    page_size: int


class RecordDetailResponse(RecordItem):
    abstract: str | None = None
    mesh_headings: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    language: str | None = None
    decisions: list[RecordDecisionSummary] = Field(default_factory=list)
    suggestions: list[RecordSuggestionSummary] = Field(default_factory=list)
    pico_spans: list[PicoSpanItem] = Field(default_factory=list)
    cluster_members: list[RecordItem] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
