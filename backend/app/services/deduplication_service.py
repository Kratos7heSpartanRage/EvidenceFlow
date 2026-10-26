"""Persist machine evaluations and snapshots; return conflicts for A's decision service."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Literal, Protocol

from ..engines import dedup
from ..engines.types import PairResult, RecordLite, fingerprint


@dataclass(frozen=True, slots=True)
class PairDecision:
    record_a_id: int
    record_b_id: int
    decision: Literal["confirm", "reject"]

    def __post_init__(self) -> None:
        if self.decision not in {"confirm", "reject"}:
            raise ValueError("Unknown pair decision")
        if self.record_a_id == self.record_b_id:
            raise ValueError("A record cannot be paired with itself")


@dataclass(frozen=True, slots=True)
class PairEvaluation:
    input_fingerprint: str
    algo_version: str
    record_ids: tuple[int, ...]
    pairs: tuple[PairResult, ...]


@dataclass(frozen=True, slots=True)
class GroupSnapshot:
    group_key: str
    member_ids: tuple[int, ...]
    representative_id: int


@dataclass(frozen=True, slots=True)
class RejectedPairConflict:
    fingerprint: str
    record_a_id: int
    record_b_id: int
    path: tuple[int, ...]
    kind: str = "pair_override_bypassed"


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    evaluation: PairEvaluation
    groups: tuple[GroupSnapshot, ...]
    conflicts: tuple[RejectedPairConflict, ...]


class DeduplicationRepository(Protocol):
    """All methods are review-scoped by the repository instance.

    Store evaluations append-only, uniquely by input_fingerprint. Store snapshots
    immutably by run_id. Repeated identical writes must be no-ops; differing
    contents under an existing run_id must raise. Do not delete historical pairs.
    These methods participate in the caller's transaction and must not commit.
    """

    def save_pair_evaluation(self, evaluation: PairEvaluation) -> None: ...

    def save_group_snapshot(self, run_id: int, groups: tuple[GroupSnapshot, ...]) -> None: ...


def _path(adjacency: dict[int, set[int]], start: int, end: int) -> tuple[int, ...]:
    queue, parent = deque([start]), {start: None}
    while queue:
        current = queue.popleft()
        if current == end:
            result = []
            while current is not None:
                result.append(current)
                current = parent[current]
            return tuple(reversed(result))
        for neighbor in sorted(adjacency[current]):
            if neighbor not in parent:
                parent[neighbor] = current
                queue.append(neighbor)
    return ()


class DeduplicationService:
    def __init__(self, repository: DeduplicationRepository) -> None:
        self.repository = repository

    def run(
        self, records: list[RecordLite], *, run_id: int,
        pair_decisions: Iterable[PairDecision] = (), pinned_record_ids: Iterable[int] = (),
        include_fuzzy: bool = False,
    ) -> DeduplicationResult:
        """Re-evaluate the complete active set; never reuse stale historical edges.

        This baseline intentionally scores the full capped set. score_pairs also
        exposes changed_ids for a future incremental adapter that can invalidate
        old pair evaluations safely. Historical evaluations never supply edges.
        """
        by_id = {record.id: record for record in records}
        pairs = tuple(dedup.score_pairs(records, include_fuzzy=include_fuzzy))
        evaluation = PairEvaluation(fingerprint({
            "records": sorted((record.id, record.input_hash) for record in records),
            "include_fuzzy": include_fuzzy, "algo_version": dedup.ALGO_VERSION,
        }), dedup.ALGO_VERSION, tuple(sorted(by_id)), pairs)
        edges = {(pair.record_a_id, pair.record_b_id) for pair in pairs if pair.tier == "auto"}
        overrides: dict[tuple[int, int], str] = {}
        for decision in pair_decisions:
            # Decisions for records outside this workspace stay in history.
            if decision.record_a_id not in by_id or decision.record_b_id not in by_id:
                continue
            pair = tuple(sorted((decision.record_a_id, decision.record_b_id)))
            if pair in overrides:
                raise ValueError("Supply exactly one current decision per pair")
            overrides[pair] = decision.decision
        rejected = set()
        for pair, decision in overrides.items():
            if decision == "confirm":
                edges.add(pair)
            else:
                edges.discard(pair)
                rejected.add(pair)
        pins = set(pinned_record_ids)
        snapshots = tuple(GroupSnapshot(
            dedup.group_key(members), tuple(sorted(members)),
            dedup.representative((by_id[member] for member in members), pins),
        ) for members in dedup.group(by_id, edges))
        adjacency = {record_id: set() for record_id in by_id}
        for a_id, b_id in edges:
            adjacency[a_id].add(b_id)
            adjacency[b_id].add(a_id)
        conflicts = []
        for a_id, b_id in sorted(rejected):
            path = _path(adjacency, a_id, b_id)
            if path:
                conflicts.append(RejectedPairConflict(
                    fingerprint(["pair_override_bypassed", a_id, b_id]), a_id, b_id, path,
                ))
        result = DeduplicationResult(evaluation, snapshots, tuple(conflicts))
        self.repository.save_pair_evaluation(evaluation)
        self.repository.save_group_snapshot(run_id, snapshots)
        return result
