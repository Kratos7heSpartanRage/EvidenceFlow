"""Shared contracts between literature-source adapters and the rest of the backend.

PROPOSAL (Member B): Member A owns the final shared contracts. These models are
what the adapters produce and consume today; if Member A changes field names,
update this file, the adapters and docs/API_CONTRACTS.md in the same PR.

Adapters only ever return these plain models. They never touch the database.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceName(StrEnum):
    EUROPE_PMC = "europe_pmc"
    PUBMED = "pubmed"


class QuerySpec(BaseModel):
    """One immutable search configuration (the input side of a query version)."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    # Boolean query, e.g. ("type 2 diabetes" OR T2DM) AND metformin
    expression: str
    date_from: date | None = None
    date_to: date | None = None
    # Europe PMC expands queries with MeSH synonyms when this is on. We always
    # send the flag explicitly so results never depend on the API's default.
    expand_synonyms: bool = False
    # Match terms only in titles and abstracts. Europe PMC otherwise also
    # searches open-access full text, which inflates hits with papers that only
    # mention a term in passing. PubMed never searches full text, so its adapter
    # ignores this flag.
    title_abstract_only: bool = False

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
    year: int | None = None
    publication_date: str | None = None  # ISO "YYYY-MM-DD" when the source gives one
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    language: str | None = None  # lowercase code as given by the source, e.g. "eng"
    pub_types: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict, description="Original source payload, kept for audit")


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
