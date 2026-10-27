"""Core immutable contracts and data structures.

Enforces cross-module boundaries between API, adapters, engines, and services.
All adapter implementations MUST return RecordIn instances only.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LiteratureSource(str, Enum):
    EUROPE_PMC = "europe_pmc"
    PUBMED = "pubmed"


class ScreeningDecisionType(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    MAYBE = "maybe"
    UNSCREENED = "unscreened"


class DecisionOrigin(str, Enum):
    HUMAN = "human"
    INHERITED = "inherited"
    CONFLICT_RESOLUTION = "conflict_resolution"


class PICOElement(str, Enum):
    P = "P"
    I = "I"
    C = "C"
    O = "O"


class AnnotationOrigin(str, Enum):
    MACHINE = "machine"
    HUMAN = "human"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DuplicateTier(str, Enum):
    TIER_1_EXACT = "tier_1_exact"
    TIER_2_HIGH_CONFIDENCE = "tier_2_high_confidence"
    TIER_3_REVIEW_NEEDED = "tier_3_review_needed"


class DuplicateDecisionType(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"


class ConflictStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


# --- Adapter & Engine Input/Output Contracts ---


class QuerySpec(BaseModel):
    """Immutable specification defining a query execution against an external source."""

    expression: str = Field(..., description="Boolean query expression")
    source: LiteratureSource = Field(..., description="External target database")
    synonyms: bool = Field(default=True, description="Enable MeSH & synonym expansion")
    date_from: str | None = Field(default=None, description="ISO date lower bound (YYYY-MM-DD)")
    date_to: str | None = Field(default=None, description="ISO date upper bound (YYYY-MM-DD)")
    language: str | None = Field(default="eng", description="Language filter")


class RecordIn(BaseModel):
    """Normalized bibliographic record returned exclusively by external source adapters."""

    source: LiteratureSource
    source_record_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    pmid: str | None = None
    abstract: str | None = None
    mesh_headings: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    language: str | None = "eng"
    raw_payload: dict[str, Any] | None = None


# --- Pure Engine Dataclasses (Engine -> Service boundary) ---


@dataclass(frozen=True)
class ScoredPair:
    """Candidate duplicate pair scored by pure deduplication engine."""

    record_a_id: str
    record_b_id: str
    similarity_score: float
    tier: DuplicateTier
    match_reasons: list[str]


@dataclass(frozen=True)
class HeuristicSuggestion:
    """Screening recommendation computed by pure screening heuristics engine."""

    record_id: str
    suggested_decision: ScreeningDecisionType
    confidence: float
    matched_criterion_id: str | None = None
    matched_criterion_label: str | None = None
    evidence_snippets: list[str] = field(default_factory=list)
    algorithm_version: str = "v1.0-rules"


@dataclass(frozen=True)
class ExtractedSpan:
    """PICO entity span extracted by pure PICO extraction engine."""

    element: PICOElement
    text: str
    start_index: int
    end_index: int
    confidence: float
