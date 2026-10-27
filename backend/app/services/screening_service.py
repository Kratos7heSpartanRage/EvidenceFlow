"""Cache machine suggestions and report staleness without writing human rows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from ..engines import screening
from ..engines.types import (
    CriterionSpec,
    Decision,
    PicoTerms,
    RecordId,
    RecordLite,
    Suggestion,
    fingerprint,
    record_id_key,
)


@dataclass(frozen=True, slots=True)
class SuggestionKey:
    record_id: RecordId
    criteria_version_id: RecordId
    content_hash: str
    algo_version: str
    context_hash: str


@dataclass(frozen=True, slots=True)
class HumanDecision:
    record_id: RecordId
    decision: Decision
    criteria_version_id: RecordId
    criterion_id: RecordId | None = None
    reason_text: str | None = None
    content_hash: str | None = None
    context_hash: str | None = None

    def __post_init__(self) -> None:
        if self.decision not in {"include", "exclude", "maybe"}:
            raise ValueError("Unknown screening decision")
        if (
            self.decision == "exclude"
            and self.criterion_id is None
            and not (self.reason_text or "").strip()
        ):
            raise ValueError("A human exclusion requires a criterion or a reason")


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    key: SuggestionKey
    suggestion: Suggestion
    cached: bool
    stale_reasons: tuple[str, ...]


class ScreeningRepository(Protocol):
    """Review-scoped, machine-only storage; insert atomically on the complete key.

    No commits, audit writes, human decision mutations, or destructive updates.
    Existing identical rows are returned; conflicting payloads must raise.
    """

    def get_suggestion(self, key: SuggestionKey) -> Suggestion | None: ...

    def save_suggestion(self, key: SuggestionKey, suggestion: Suggestion) -> None: ...


class ScreeningService:
    def __init__(self, repository: ScreeningRepository) -> None:
        self.repository = repository

    def run(
        self,
        records: list[RecordLite],
        criteria: list[CriterionSpec],
        *,
        criteria_version_id: RecordId,
        pico_terms: PicoTerms,
        human_decisions: Mapping[RecordId, HumanDecision] | None = None,
    ) -> tuple[ScreeningResult, ...]:
        if len({record.id for record in records}) != len(records):
            raise ValueError("Record ids must be unique")
        if len({criterion.id for criterion in criteria}) != len(criteria):
            raise ValueError("Criterion ids must be unique")
        context_hash = fingerprint(
            {
                "pico_terms": pico_terms.input_hash,
                "criteria": [
                    criterion.serializable()
                    for criterion in sorted(criteria, key=lambda c: record_id_key(c.id))
                ],
            }
        )
        active_criteria = {criterion.id for criterion in criteria if criterion.is_active}
        decisions = human_decisions or {}
        result = []
        for record in sorted(records, key=lambda item: record_id_key(item.id)):
            key = SuggestionKey(
                record.id,
                criteria_version_id,
                record.input_hash,
                screening.ALGO_VERSION,
                context_hash,
            )
            suggestion = self.repository.get_suggestion(key)
            cached = suggestion is not None
            if suggestion is None:
                suggestion = screening.screen(record, criteria, pico_terms)
                self.repository.save_suggestion(key, suggestion)
            stale = []
            human = decisions.get(record.id)
            if human is not None:
                if human.record_id != record.id:
                    raise ValueError("Human decision key does not match its record id")
                if human.criterion_id is not None and human.criterion_id not in active_criteria:
                    stale.append("criterion_removed_or_inactive")
                inputs_changed = (
                    human.criteria_version_id != criteria_version_id
                    or (human.content_hash is not None and human.content_hash != key.content_hash)
                    or (human.context_hash is not None and human.context_hash != context_hash)
                )
                # An intentional override of the current suggestion is not stale.
                # Capture these hashes with the human decision to detect later
                # content/term changes even when the criteria version is unchanged.
                if inputs_changed and human.decision != suggestion.decision:
                    stale.append("suggestion_disagrees")
            result.append(ScreeningResult(key, suggestion, cached, tuple(stale)))
        return tuple(result)
