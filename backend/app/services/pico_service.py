"""Persist complete machine annotation batches, including unknown labels."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from ..engines import pico
from ..engines.types import Decision, PicoTerms, RecordId, RecordLite, SpanSuggestion, record_id_key


@dataclass(frozen=True, slots=True)
class PicoKey:
    record_id: RecordId
    content_hash: str
    algo_version: str
    terms_hash: str


@dataclass(frozen=True, slots=True)
class PicoResult:
    key: PicoKey
    annotations: tuple[SpanSuggestion, ...]
    cached: bool


class PicoRepository(Protocol):
    """Machine batches only; a review-scoped implementation is supplied by A.

    None means no batch exists, whereas an existing batch may contain unknowns.
    Store the full batch atomically and uniquely by key. Never supersede or edit
    human annotations. The caller owns transactions and effective-span selection.
    """

    def get_machine_annotations(self, key: PicoKey) -> tuple[SpanSuggestion, ...] | None: ...

    def save_machine_annotations(
        self, key: PicoKey, annotations: tuple[SpanSuggestion, ...]
    ) -> None: ...


class PicoService:
    def __init__(self, repository: PicoRepository) -> None:
        self.repository = repository

    def run(
        self,
        records: list[RecordLite],
        *,
        decisions: Mapping[RecordId, Decision],
        pico_terms: PicoTerms,
    ) -> tuple[PicoResult, ...]:
        """Process representative records whose effective status is Include/Maybe.

        The caller resolves human-over-machine precedence and open conflicts.
        Unscreened, excluded, and conflicting groups must not be sent as eligible.
        """
        if len({record.id for record in records}) != len(records):
            raise ValueError("Record ids must be unique")
        if any(value not in {"include", "exclude", "maybe"} for value in decisions.values()):
            raise ValueError("Unknown effective screening decision")
        result = []
        for record in sorted(records, key=lambda item: record_id_key(item.id)):
            if decisions.get(record.id) not in {"include", "maybe"}:
                continue
            key = PicoKey(record.id, record.input_hash, pico.ALGO_VERSION, pico_terms.input_hash)
            annotations = self.repository.get_machine_annotations(key)
            cached = annotations is not None
            if annotations is None:
                annotations = tuple(pico.extract_pico(record.abstract, pico_terms))
                self.repository.save_machine_annotations(key, annotations)
            result.append(PicoResult(key, annotations, cached))
        return tuple(result)
