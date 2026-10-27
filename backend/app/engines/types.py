"""Member C boundary types, to be mapped from Member A's API/ORM models.

No web framework, ORM, network client, or other application module is imported.
Offsets in SpanSuggestion use Python Unicode code points, with an exclusive end.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any, Literal

RecordId = int | str


def record_id_key(value: RecordId) -> tuple[int, int | str]:
    return (0, value) if isinstance(value, int) else (1, value)


Decision = Literal["include", "exclude", "maybe"]
Label = Literal["P", "I", "C", "O"]
Detector = Literal["metadata", "rule", "metadata_then_rule", "manual_only"]


def fingerprint(value: Any) -> str:
    """Stable identifier for JSON-compatible inputs (never Python's salted hash)."""
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _terms(values: tuple[str, ...] | str) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


@dataclass(frozen=True, slots=True)
class RecordLite:
    id: RecordId
    title: str = ""
    abstract: str | None = None
    doi: str | None = None
    pmid: str | int | None = None
    year: int | None = None
    first_author: str | None = None
    authors: tuple[str, ...] = ()
    journal: str | None = None
    language: str | None = None
    pub_types: tuple[str, ...] = ()
    mesh: tuple[str, ...] = ()
    source: str = ""
    content_hash: str | None = None

    def __post_init__(self) -> None:
        if not (
            (isinstance(self.id, int) and not isinstance(self.id, bool) and self.id > 0)
            or (isinstance(self.id, str) and bool(self.id.strip()))
        ):
            raise ValueError("Record ids must be positive integers or nonempty internal strings")
        if self.year is not None and (
            not isinstance(self.year, int) or isinstance(self.year, bool)
        ):
            raise ValueError("year must be an integer or None")
        for name in ("authors", "pub_types", "mesh"):
            value = getattr(self, name)
            if isinstance(value, str):
                value = (value,)
            object.__setattr__(self, name, tuple(value))

    @property
    def input_hash(self) -> str:
        # Include all supplied fields even if ingestion supplied a content_hash.
        # An incomplete upstream hash must not let a metadata change use stale output.
        return fingerprint(asdict(self))


@dataclass(frozen=True, slots=True)
class PicoTerms:
    population: tuple[str, ...] = ()
    intervention: tuple[str, ...] = ()
    comparator: tuple[str, ...] = ()
    outcome: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("population", "intervention", "comparator", "outcome"):
            object.__setattr__(self, name, _terms(getattr(self, name)))

    @property
    def input_hash(self) -> str:
        return fingerprint(asdict(self))


@dataclass(frozen=True, slots=True)
class CriterionSpec:
    id: RecordId
    code: str
    kind: Literal["include", "exclude"] = "exclude"
    reason: str = ""
    detector: Detector = "metadata_then_rule"
    is_active: bool = True
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in {"include", "exclude"}:
            raise ValueError("Unknown criterion kind")
        if self.detector not in {"metadata", "rule", "metadata_then_rule", "manual_only"}:
            raise ValueError("Unknown detector")
        if not self.reason.strip():
            raise ValueError("Each criterion needs a review-specific reason")

        # Freeze a JSON copy so a caller cannot mutate parameters behind a cache key.
        def freeze(value: Any) -> Any:
            if isinstance(value, dict):
                return MappingProxyType({key: freeze(item) for key, item in value.items()})
            if isinstance(value, list):
                return tuple(freeze(item) for item in value)
            return value

        object.__setattr__(self, "params", freeze(json.loads(json.dumps(dict(self.params)))))

    def serializable(self) -> dict[str, Any]:
        def thaw(value: Any) -> Any:
            if isinstance(value, Mapping):
                return {key: thaw(item) for key, item in value.items()}
            if isinstance(value, tuple):
                return [thaw(item) for item in value]
            return value

        return {
            "id": self.id,
            "code": self.code,
            "kind": self.kind,
            "reason": self.reason,
            "detector": self.detector,
            "is_active": self.is_active,
            "params": thaw(self.params),
        }


@dataclass(frozen=True, slots=True)
class PairResult:
    record_a_id: RecordId
    record_b_id: RecordId
    method: str
    score: float
    tier: Literal["auto", "uncertain"]
    matched_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class Evidence:
    code: str
    source: Literal["metadata", "rule", "manual"]
    field: str
    matched: tuple[str, ...]
    explanation: str
    criterion_id: RecordId | None = None


@dataclass(frozen=True, slots=True)
class Suggestion:
    decision: Decision
    strength: Literal["strong", "weak", "none"]
    criterion_id: RecordId | None
    evidence: tuple[Evidence, ...]
    algo_version: str


@dataclass(frozen=True, slots=True)
class SpanSuggestion:
    label: Label
    text: str | None
    start_char: int | None
    end_char: int | None
    status: Literal["suggested", "unknown"]
    rule: str
