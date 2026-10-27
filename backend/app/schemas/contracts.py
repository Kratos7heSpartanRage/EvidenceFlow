"""Shared contracts between literature-source adapters and the rest of the backend.

PROPOSAL (Member B): Member A owns the final shared contracts. These models are
what the adapters produce and consume today; if Member A changes field names,
update this file, the adapters and docs/API_CONTRACTS.md in the same PR.

Adapters only ever return these plain models. They never touch the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, StrEnum
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceName(StrEnum):
    EUROPE_PMC = "europe_pmc"
    PUBMED = "pubmed"


class QuerySpec(BaseModel):
    """One immutable search configuration (the input side of a query version)."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    # Boolean query, e.g. ("type 2 diabetes" OR T2DM) AND metformin
    expression: str = Field(min_length=1, max_length=2000)
    date_from: date | None = None
    date_to: date | None = None
    # Europe PMC expands queries with MeSH synonyms when this is on. We always
    # send the flag explicitly so results never depend on the API's default.
    expand_synonyms: bool = Field(
        default=False, validation_alias=AliasChoices("expand_synonyms", "synonyms")
    )
    # Match terms only in titles and abstracts. Europe PMC otherwise also
    # searches open-access full text, which inflates hits with papers that only
    # mention a term in passing. PubMed never searches full text, so its adapter
    # ignores this flag.
    title_abstract_only: bool = False
    language: str | None = "eng"

    @property
    def synonyms(self) -> bool:
        return self.expand_synonyms

    @field_validator("expression")
    @classmethod
    def _expression_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("expression must not be empty")
        return value

    @model_validator(mode="after")
    def _date_range_valid(self) -> QuerySpec:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self


class Author(BaseModel):
    full_name: str
    last_name: str | None = None
    initials: str | None = None


class RecordIn(BaseModel):
    """A literature record normalised from a source, before it is stored.

    Missing fields are None (or empty lists), never invented. Identifiers are
    trimmed but otherwise left as the source gave them; deduplication applies
    its own normalisation.
    """

    source: SourceName
    # Unique within `source`. Europe PMC: "<SRC>:<id>", e.g. "MED:12345678".
    source_record_id: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    title: str
    abstract: str | None = None
    authors: list[Author] = Field(default_factory=list)
    year: int | None = Field(
        default=None, validation_alias=AliasChoices("year", "publication_year")
    )
    publication_date: str | None = None  # ISO "YYYY-MM-DD" when the source gives one
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    language: str | None = None  # lowercase code as given by the source, e.g. "eng"
    pub_types: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices("pub_types", "publication_types")
    )
    mesh_terms: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices("mesh_terms", "mesh_headings")
    )
    keywords: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("raw", "raw_payload"),
        description="Original source payload, kept for audit",
    )

    @field_validator("authors", mode="before")
    @classmethod
    def _legacy_author_names(cls, values):
        return [{"full_name": item} if isinstance(item, str) else item for item in values]

    @field_validator("raw", mode="before")
    @classmethod
    def _empty_raw(cls, value):
        return value or {}

    @property
    def publication_year(self):
        return self.year

    @property
    def mesh_headings(self):
        return self.mesh_terms

    @property
    def publication_types(self):
        return self.pub_types

    @property
    def raw_payload(self):
        return self.raw


class SearchResult(BaseModel):
    """Output of an adapter search used for import.

    `ids` is every source_record_id the search returned (up to the cap), in rank
    order. `records` holds only the records that were not already known, which
    is what makes the fetch incremental.
    """

    hit_count: int
    ids: list[str]
    records: list[RecordIn]
    skipped_known: int = 0
    truncated: bool = False  # True when hit_count exceeded the import cap
    warnings: list[str] = Field(default_factory=list)


class PreviewResult(BaseModel):
    hit_count: int
    records: list[RecordIn]
    warnings: list[str] = Field(default_factory=list)


# Compatibility for the initial API/model vocabulary.
LiteratureSource = SourceName


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
    AWAITING_PROCESSING = "awaiting_processing"
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


# Legacy DTOs retained for existing callers; engines use app.engines.types.
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
