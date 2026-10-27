"""Query Strategy and Versioning Pydantic schemas."""

from datetime import datetime
from typing import Any

from backend.app.schemas.contracts import LiteratureSource
from pydantic import BaseModel, ConfigDict, Field


class QuerySpecSchema(BaseModel):
    expression: str = Field(
        ..., min_length=1, max_length=2000, description="Boolean query expression"
    )
    source: LiteratureSource = Field(..., description="Target literature source")
    synonyms: bool = Field(default=True, description="Enable MeSH & synonym expansion")
    date_from: str | None = Field(default=None, description="ISO date lower bound (YYYY-MM-DD)")
    date_to: str | None = Field(default=None, description="ISO date upper bound (YYYY-MM-DD)")
    language: str | None = Field(default="eng", description="Language filter")


class QueryCreate(BaseModel):
    label: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Descriptive label, e.g. 'v1.0 — Initial targeted search'",
    )
    parent_id: str | None = Field(default=None, description="Parent query version ID if iterating")
    spec: QuerySpecSchema


class QueryResponse(BaseModel):
    id: str
    review_id: str
    parent_id: str | None = None
    version_number: int
    label: str
    expression: str
    source: str
    synonyms: bool
    date_from: str | None = None
    date_to: str | None = None
    language: str | None = "eng"
    status: str
    hit_count: int | None = None
    imported_count: int | None = None
    created_at: datetime
    frozen_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class QueryPreviewResponse(BaseModel):
    query_id: str
    estimated_hits: int
    sample_records: list[dict[str, Any]] = Field(default_factory=list)
    is_frozen: bool = True


class QueryImportResponse(BaseModel):
    run_id: str
    status: str = "queued"


class QueryDiffResponse(BaseModel):
    query_v1_id: str
    query_v2_id: str
    new_records_count: int
    retained_records_count: int
    dropped_records_count: int
    already_screened_retained_count: int
    potential_conflicts_count: int
