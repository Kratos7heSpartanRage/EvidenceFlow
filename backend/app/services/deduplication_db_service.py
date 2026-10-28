"""Database workflows for duplicate review; C's repository-based service stays separate.

Historical groups and snapshots are preserved. A conservative, deterministic
partition honors the latest human cannot-link decisions and exposes blocked
transitive bridges as unresolved conflicts. No human screening rows are touched.
"""

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session, joinedload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.engines.dedup import (
    ALGO_VERSION,
    group_key,
    group_with_rejections,
    representative,
    score_pairs,
)
from app.models.dedup import DedupGroup, DuplicatePair, GroupSnapshot, PairDecision
from app.models.loop import Conflict
from app.models.query import QueryRecord, QueryVersion
from app.models.record import Record
from app.models.review import Review
from app.schemas.contracts import DuplicateTier, ScoredPair
from app.schemas.dedup import (
    DuplicatePairResponse,
    PairDecisionIn,
    PairDecisionResponse,
    PairDecisionResult,
    RecordSummary,
)
from app.services.audit_service import AuditService
from app.services.record_mapping import to_engine_record


def _latest(decisions):
    return max(
        decisions, key=lambda item: (item.created_at.replace(tzinfo=None), item.id), default=None
    )


def find_transitive_conflict_path(
    start: str,
    end: str,
    edges: list[tuple[str, str]],
) -> list[str] | None:
    """Finds the shortest transitive path between start and end using BFS for conflict visualization."""
    from collections import deque

    adj: dict[str, list[str]] = {}
    for u, v in edges:
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)

    queue = deque([[start]])
    visited = {start}

    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == end:
            return path
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None


class DatabaseDeduplicationService:
    def __init__(self, db: Session):
        self.db = db

    def _review(self, review_id: str) -> None:
        if self.db.get(Review, review_id) is None:
            raise NotFoundError(f"Review '{review_id}' was not found.")

    def _records(self, review_id: str) -> list[Record]:
        return (
            self.db.query(Record)
            .filter(Record.review_id == review_id, Record.is_hidden.is_(False))
            .order_by(Record.id)
            .all()
        )

    def ingest_candidate_pairs(
        self,
        review_id: str,
        scored_pairs: list[ScoredPair],
        *,
        commit: bool = True,
    ) -> list[DuplicatePair]:
        self._review(review_id)
        valid_ids = {record.id for record in self.db.query(Record).filter_by(review_id=review_id)}
        inputs = {}
        allowed_tiers = {tier.value for tier in DuplicateTier}
        for pair in scored_pairs:
            a, b = sorted((pair.record_a_id, pair.record_b_id))
            if a == b or a not in valid_ids or b not in valid_ids:
                raise ValidationError("Pair endpoints must be distinct records from this review.")
            tier = pair.tier.value if hasattr(pair.tier, "value") else str(pair.tier)
            if tier not in allowed_tiers or not 0 <= pair.similarity_score <= 1:
                raise ValidationError("Invalid candidate tier or similarity score.")
            value = (pair.similarity_score, tier, pair.match_reasons)
            if (a, b) in inputs and inputs[a, b] != value:
                raise ValidationError("The same pair has conflicting inputs in this batch.")
            inputs[a, b] = value
        current = {
            (pair.record_a_id, pair.record_b_id): pair
            for pair in (self.db.query(DuplicatePair).filter_by(review_id=review_id).all())
        }
        # The initial schema has no evaluation revision key. Reject changing
        # machine evidence rather than silently overwriting the only history.
        for key, value in inputs.items():
            old = current.get(key)
            if (
                old is not None
                and old.status == "pending"
                and (old.similarity_score, old.tier, old.match_reasons) != value
            ):
                raise ConflictError(
                    "Changed pair evidence requires versioned evaluation storage.",
                    code="PAIR_EVALUATION_CHANGED",
                )
        result = []
        for (a, b), (score, tier, reasons) in sorted(inputs.items()):
            pair = current.get((a, b))
            if pair is None:
                pair = DuplicatePair(
                    review_id=review_id,
                    record_a_id=a,
                    record_b_id=b,
                    similarity_score=score,
                    tier=tier,
                    match_reasons=reasons,
                    status="pending",
                )
                self.db.add(pair)
            result.append(pair)
        self.db.flush()
        if commit:
            self.db.commit()
        return result

    def score_current_records(self, review_id: str) -> None:
        """Translate C's actual engine output, with no synthetic candidate scores."""
        records = [to_engine_record(record) for record in self._records(review_id)]
        candidates = [
            ScoredPair(
                record_a_id=pair.record_a_id,
                record_b_id=pair.record_b_id,
                similarity_score=pair.score,
                tier=DuplicateTier.TIER_1_EXACT
                if pair.tier == "auto"
                else DuplicateTier.TIER_3_REVIEW_NEEDED,
                match_reasons=[
                    f"algorithm:{ALGO_VERSION}",
                    f"method:{pair.method}",
                    *[f"matched:{field}" for field in pair.matched_fields],
                    *[f"conflict:{field}" for field in pair.conflicting_fields],
                    pair.explanation,
                ],
            )
            for pair in score_pairs(records)
        ]
        self.ingest_candidate_pairs(review_id, candidates, commit=False)

    def cluster_records(self, review_id: str, *, commit: bool = True) -> dict[str, Any]:
        self._review(review_id)
        records = self._records(review_id)
        record_map = {record.id: record for record in records}
        pairs = (
            self.db.query(DuplicatePair)
            .populate_existing()
            .options(joinedload(DuplicatePair.decisions))
            .filter_by(review_id=review_id)
            .all()
        )
        edges, rejected = [], set()
        for pair in pairs:
            a, b = pair.record_a_id, pair.record_b_id
            if a not in record_map or b not in record_map:
                continue
            latest = _latest(pair.decisions)
            if latest is not None and latest.decision == "reject":
                rejected.add(tuple(sorted((a, b))))
            elif latest is not None and latest.decision == "confirm":
                edges.append((0, -pair.similarity_score, *sorted((a, b))))
            elif pair.tier == DuplicateTier.TIER_1_EXACT.value:
                edges.append((1, -pair.similarity_score, *sorted((a, b))))

        components, blocked = group_with_rejections(
            record_map,
            [(edge[2], edge[3]) for edge in edges],
            rejected,
            preferred_edges=[(edge[2], edge[3]) for edge in edges if edge[0] == 0],
        )
        for member_ids in components:
            component = [record_map[record_id] for record_id in sorted(member_ids)]
            group_id = str(
                uuid5(
                    NAMESPACE_URL, f"evidenceflow:{review_id}:{group_key(r.id for r in component)}"
                )
            )
            canonical = representative(to_engine_record(record) for record in component)
            group = self.db.get(DedupGroup, group_id)
            if group is None:
                group = DedupGroup(id=group_id, review_id=review_id, canonical_record_id=canonical)
                self.db.add(group)
            elif group.canonical_record_id != canonical:
                group.canonical_record_id = canonical
            self.db.flush()
            for record in component:
                record.group_id = group_id
                record.is_representative = record.id == canonical

        for a, b in sorted(blocked):
            fingerprint = f"{review_id}:pair_override:{a}:{b}"
            if self.db.query(Conflict).filter_by(open_fingerprint=fingerprint).first() is None:
                path = find_transitive_conflict_path(a, b, [(edge[2], edge[3]) for edge in edges])
                path_str = " -> ".join(path) if path else f"{a} <-> {b}"
                self.db.add(
                    Conflict(
                        review_id=review_id,
                        group_id=record_map[a].group_id,
                        reason="pair_override_bypassed",
                        status="open",
                        open_fingerprint=fingerprint,
                        resolution_note=f"Transitive conflict link: {path_str}. Human rejected pair ({a}, {b}) was transitively connected by machine edges.",
                    )
                )
        self.db.flush()
        # Old groups remain as historical identities referenced by snapshots.
        if commit:
            self.db.commit()
        return {"total_records": len(records), "groups_count": len(components)}

    def record_pair_decision(
        self,
        review_id: str,
        data: PairDecisionIn,
        actor: str = "Reviewer",
    ) -> PairDecisionResult:
        self._review(review_id)
        if data.duplicate_pair_id:
            pair = (
                self.db.query(DuplicatePair)
                .filter_by(id=data.duplicate_pair_id, review_id=review_id)
                .first()
            )
            if pair is None:
                raise NotFoundError("Candidate duplicate pair was not found.")
        else:
            a, b = sorted((data.record_a_id, data.record_b_id))
            records = (
                self.db.query(Record)
                .filter(Record.review_id == review_id, Record.id.in_([a, b]))
                .all()
            )
            if len(records) != 2:
                raise ValidationError("Pair endpoints must belong to this review.")
            pair = (
                self.db.query(DuplicatePair)
                .filter_by(review_id=review_id, record_a_id=a, record_b_id=b)
                .first()
            )
            if pair is None:
                pair = DuplicatePair(
                    review_id=review_id,
                    record_a_id=a,
                    record_b_id=b,
                    similarity_score=0.0,
                    tier=DuplicateTier.TIER_3_REVIEW_NEEDED.value,
                    match_reasons=["manual_pair; not a machine similarity estimate"],
                    status="pending",
                )
                self.db.add(pair)
                self.db.flush()
        latest = (
            self.db.query(PairDecision)
            .filter_by(duplicate_pair_id=pair.id)
            .order_by(PairDecision.created_at.desc(), PairDecision.id.desc())
            .first()
        )
        reviewer = data.reviewer_name or actor
        decision_value = data.decision.value
        record_a = self.db.get(Record, pair.record_a_id)
        if latest and (latest.decision, latest.reviewer_name, latest.note) == (
            decision_value,
            reviewer,
            data.note,
        ):
            return PairDecisionResult(
                decision_id=latest.id,
                duplicate_pair_id=pair.id,
                affected_group_id=record_a.group_id,
            )
        before = {"status": pair.status, "decision_id": latest.id if latest else None}
        pair.status = "confirmed_duplicate" if decision_value == "confirm" else "rejected_different"
        decision = PairDecision(
            duplicate_pair_id=pair.id,
            decision=decision_value,
            reviewer_name=reviewer,
            note=data.note,
        )
        try:
            self.db.add(decision)
            self.db.flush()
            self.cluster_records(review_id, commit=False)
            # AuditService commits the verdict, regroup and audit atomically.
            AuditService(self.db).log(
                review_id=review_id,
                actor=reviewer,
                event_type="pair_decision_recorded",
                target_type="duplicate_pair",
                target_id=pair.id,
                before_state=before,
                after_state={
                    "status": pair.status,
                    "decision": decision_value,
                    "decision_id": decision.id,
                    "affected_group_id": record_a.group_id,
                },
                note=data.note,
            )
        except Exception:
            self.db.rollback()
            raise
        return PairDecisionResult(
            decision_id=decision.id, duplicate_pair_id=pair.id, affected_group_id=record_a.group_id
        )

    def get_duplicate_pairs(
        self, review_id: str, tier: str | None = None, decided: bool | None = None
    ) -> list[DuplicatePairResponse]:
        self._review(review_id)
        query = (
            self.db.query(DuplicatePair)
            .options(
                joinedload(DuplicatePair.record_a),
                joinedload(DuplicatePair.record_b),
                joinedload(DuplicatePair.decisions),
            )
            .filter_by(review_id=review_id)
        )
        if tier:
            query = query.filter(DuplicatePair.tier == tier)
        if decided is False:
            query = query.filter(DuplicatePair.status == "pending")
        elif decided is True:
            query = query.filter(DuplicatePair.status != "pending")
        return [
            DuplicatePairResponse(
                id=pair.id,
                review_id=pair.review_id,
                record_a_id=pair.record_a_id,
                record_b_id=pair.record_b_id,
                record_a=RecordSummary.model_validate(pair.record_a),
                record_b=RecordSummary.model_validate(pair.record_b),
                similarity_score=pair.similarity_score,
                tier=pair.tier,
                match_reasons=pair.match_reasons,
                status=pair.status,
                created_at=pair.created_at,
                decisions=[
                    PairDecisionResponse.model_validate(item)
                    for item in sorted(
                        pair.decisions, key=lambda d: (d.created_at.replace(tzinfo=None), d.id)
                    )
                ],
            )
            for pair in query.order_by(
                DuplicatePair.similarity_score.desc(), DuplicatePair.id
            ).all()
        ]

    def capture_group_snapshot(self, query_version_id: str, *, commit: bool = True) -> int:
        query = self.db.get(QueryVersion, query_version_id)
        if query is None:
            raise NotFoundError(f"Query version '{query_version_id}' was not found.")
        existing = self.db.query(GroupSnapshot).filter_by(query_version_id=query_version_id).all()
        if existing:
            return len(existing)
        records = (
            self.db.query(Record)
            .join(QueryRecord, QueryRecord.record_id == Record.id)
            .filter(
                QueryRecord.query_version_id == query_version_id,
                Record.review_id == query.review_id,
            )
            .all()
        )
        if any(not record.group_id for record in records):
            raise ConflictError("Group every query record before capturing its snapshot.")
        for record in records:
            self.db.add(
                GroupSnapshot(
                    query_version_id=query_version_id,
                    record_id=record.id,
                    group_id=record.group_id,
                    is_representative="true" if record.is_representative else "false",
                )
            )
        self.db.flush()
        if commit:
            self.db.commit()
        return len(records)
