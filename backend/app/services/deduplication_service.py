"""Deduplication and clustering service.

Handles:
1. Candidate duplicate pair ingestion and persistence.
2. Graph connected-components clustering with Scenario D guard (pair override bypass protection).
3. Deterministic canonical representative study election.
4. Human pair confirmation/rejection workflows with automatic regrouping.
5. Immutable GroupSnapshot capture for zero-API rollbacks.
"""

from collections import defaultdict, deque
from typing import Any

from backend.app.core.database import utc_now
from backend.app.core.errors import NotFoundError
from backend.app.models.dedup import DedupGroup, DuplicatePair, GroupSnapshot, PairDecision
from backend.app.models.loop import Conflict
from backend.app.models.query import QueryRecord, QueryVersion
from backend.app.models.record import Record
from backend.app.schemas.contracts import ScoredPair
from backend.app.schemas.dedup import (
    DuplicatePairResponse,
    PairDecisionIn,
    PairDecisionResponse,
    PairDecisionResult,
    RecordSummary,
)
from backend.app.services.audit_service import AuditService
from sqlalchemy.orm import Session, joinedload


class DeduplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def ingest_candidate_pairs(
        self, review_id: str, scored_pairs: list[ScoredPair]
    ) -> list[DuplicatePair]:
        """Ingests scored pairs from deduplication engine idempotently."""
        results = []
        for sp in scored_pairs:
            # Canonicalize pair order to satisfy unique constraint
            rec_a_id, rec_b_id = sorted([sp.record_a_id, sp.record_b_id])

            existing = (
                self.db.query(DuplicatePair)
                .filter(
                    DuplicatePair.review_id == review_id,
                    DuplicatePair.record_a_id == rec_a_id,
                    DuplicatePair.record_b_id == rec_b_id,
                )
                .first()
            )

            tier_str = sp.tier.value if hasattr(sp.tier, "value") else str(sp.tier)

            if existing:
                # Update score and reasons if still pending
                if existing.status == "pending":
                    existing.similarity_score = sp.similarity_score
                    existing.tier = tier_str
                    existing.match_reasons = sp.match_reasons
                results.append(existing)
            else:
                new_pair = DuplicatePair(
                    review_id=review_id,
                    record_a_id=rec_a_id,
                    record_b_id=rec_b_id,
                    similarity_score=sp.similarity_score,
                    tier=tier_str,
                    match_reasons=sp.match_reasons,
                    status="pending",
                )
                self.db.add(new_pair)
                results.append(new_pair)

        self.db.commit()
        for r in results:
            self.db.refresh(r)
        return results

    def cluster_records(self, review_id: str) -> dict[str, Any]:
        """Executes graph connected-components clustering across records in a review.

        Respects Scenario D: Human pair rejections are sovereign. If transitive
        edges connect two previously rejected records, the connection is prevented
        and a pair_override_bypassed conflict is flagged.
        """
        # 1. Fetch all visible records for this review
        records = (
            self.db.query(Record)
            .filter(Record.review_id == review_id, Record.is_hidden.is_(False))
            .all()
        )
        if not records:
            return {"total_records": 0, "groups_count": 0}

        record_map = {r.id: r for r in records}
        all_record_ids = set(record_map.keys())

        # 2. Fetch all pairs and human decisions
        pairs = (
            self.db.query(DuplicatePair)
            .options(joinedload(DuplicatePair.decisions))
            .filter(DuplicatePair.review_id == review_id)
            .all()
        )

        confirmed_edges: set[tuple[str, str]] = set()
        rejected_edges: set[tuple[str, str]] = set()

        for p in pairs:
            u, v = sorted([p.record_a_id, p.record_b_id])
            if u not in all_record_ids or v not in all_record_ids:
                continue

            # Check human decisions
            decisions = p.decisions
            has_reject = any(d.decision == "reject" for d in decisions)
            has_confirm = any(d.decision == "confirm" for d in decisions)

            if has_reject:
                rejected_edges.add((u, v))
            elif has_confirm:
                confirmed_edges.add((u, v))
            elif p.tier == "tier_1_exact":
                # Tier 1 exact matches auto-cluster unless rejected
                confirmed_edges.add((u, v))

        # 3. Build graph adjacency list
        adj: dict[str, set[str]] = defaultdict(set)
        for u, v in confirmed_edges:
            adj[u].add(v)
            adj[v].add(u)

        # 4. Find Connected Components with Scenario D Guard
        visited: set[str] = set()
        clusters: list[list[str]] = []

        for rec_id in all_record_ids:
            if rec_id in visited:
                continue

            component: list[str] = []
            component_nodes: set[str] = {rec_id}
            queue = deque([rec_id])
            visited.add(rec_id)

            while queue:
                curr = queue.popleft()
                component.append(curr)

                for neighbor in adj.get(curr, set()):
                    if neighbor not in visited and neighbor not in component_nodes:
                        # Scenario D Guard: Check if adding neighbor violates any human rejection in this component
                        violates_reject = False
                        for existing_member in component_nodes:
                            pair_key = tuple(sorted([existing_member, neighbor]))
                            if pair_key in rejected_edges:
                                violates_reject = True
                                # Flag pair_override_bypassed conflict
                                self._flag_pair_override_conflict(
                                    review_id, pair_key[0], pair_key[1]
                                )
                                break

                        if not violates_reject:
                            visited.add(neighbor)
                            component_nodes.add(neighbor)
                            queue.append(neighbor)

            clusters.append(component)

        # 5. Deterministic Canonical Representative Election & Group Updates
        groups_created_or_updated = 0
        for cluster_members in clusters:
            cluster_records = [record_map[rid] for rid in cluster_members]

            # Deterministic Sort:
            # 1. Presence of DOI (True > False)
            # 2. Presence of PMID (True > False)
            # 3. Length of abstract (longer > shorter)
            # 4. Publication year (earlier > later, 9999 if missing)
            # 5. Record UUID (tie breaker)
            sorted_records = sorted(
                cluster_records,
                key=lambda r: (
                    1 if r.doi else 0,
                    1 if r.pmid else 0,
                    len(r.abstract or ""),
                    -(r.publication_year or 9999),
                    r.id,
                ),
                reverse=True,
            )

            canonical = sorted_records[0]

            # Find or create DedupGroup
            existing_group_ids = {r.group_id for r in cluster_records if r.group_id}
            group = None
            if existing_group_ids:
                # Reuse the group of the canonical record if available, or the first existing group
                preferred_group_id = canonical.group_id or next(iter(existing_group_ids))
                group = (
                    self.db.query(DedupGroup).filter(DedupGroup.id == preferred_group_id).first()
                )

            if not group:
                group = DedupGroup(review_id=review_id, canonical_record_id=canonical.id)
                self.db.add(group)
                self.db.flush()
            else:
                group.canonical_record_id = canonical.id
                group.updated_at = utc_now()

            # Update records
            for r in cluster_records:
                r.group_id = group.id
                r.is_representative = r.id == canonical.id

            groups_created_or_updated += 1

        self.db.commit()

        # Clean up any orphaned dedup groups that have zero members
        self._cleanup_orphaned_groups(review_id)

        return {
            "total_records": len(all_record_ids),
            "groups_count": groups_created_or_updated,
        }

    def _flag_pair_override_conflict(self, review_id: str, rec_a_id: str, rec_b_id: str) -> None:
        """Flags an open conflict when a human-rejected pair is transitively bridged (Scenario D)."""
        fingerprint = f"{review_id}:pair_override:{rec_a_id}:{rec_b_id}"
        existing = (
            self.db.query(Conflict)
            .filter(Conflict.open_fingerprint == fingerprint, Conflict.status == "open")
            .first()
        )
        if not existing:
            conflict = Conflict(
                review_id=review_id,
                group_id=f"grp_override_{rec_a_id}",
                reason="pair_override_bypassed",
                status="open",
                open_fingerprint=fingerprint,
                resolution_note=f"Transitive connection bridged manually rejected pair ({rec_a_id}, {rec_b_id}). Records kept separate.",
            )
            self.db.add(conflict)
            self.db.commit()

    def _cleanup_orphaned_groups(self, review_id: str) -> None:
        """Removes empty dedup groups that lost all members due to merging."""
        orphaned = (
            self.db.query(DedupGroup)
            .filter(DedupGroup.review_id == review_id, ~DedupGroup.members.any())
            .all()
        )
        for g in orphaned:
            self.db.delete(g)
        if orphaned:
            self.db.commit()

    def record_pair_decision(
        self, review_id: str, data: PairDecisionIn, actor: str = "Reviewer"
    ) -> PairDecisionResult:
        """Records a human verdict (confirm/reject) on a duplicate pair and triggers regrouping."""
        # Find pair
        pair = None
        if data.duplicate_pair_id:
            pair = (
                self.db.query(DuplicatePair)
                .filter(
                    DuplicatePair.id == data.duplicate_pair_id, DuplicatePair.review_id == review_id
                )
                .first()
            )
        elif data.record_a_id and data.record_b_id:
            u, v = sorted([data.record_a_id, data.record_b_id])
            pair = (
                self.db.query(DuplicatePair)
                .filter(
                    DuplicatePair.review_id == review_id,
                    DuplicatePair.record_a_id == u,
                    DuplicatePair.record_b_id == v,
                )
                .first()
            )
            if not pair:
                # Create pair on the fly if user manually links/rejects unflagged pair
                pair = DuplicatePair(
                    review_id=review_id,
                    record_a_id=u,
                    record_b_id=v,
                    similarity_score=1.0 if data.decision == "confirm" else 0.0,
                    tier="tier_2_high_confidence",
                    match_reasons=["manual_user_link"],
                    status="pending",
                )
                self.db.add(pair)
                self.db.flush()

        if not pair:
            raise NotFoundError("Candidate duplicate pair was not found.")

        previous_status = pair.status
        new_status = "confirmed_duplicate" if data.decision == "confirm" else "rejected_different"
        pair.status = new_status

        # Create human pair decision row
        decision = PairDecision(
            duplicate_pair_id=pair.id,
            decision=data.decision.value if hasattr(data.decision, "value") else str(data.decision),
            reviewer_name=data.reviewer_name or actor,
            note=data.note,
        )
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)

        # Trigger graph regrouping
        self.cluster_records(review_id)

        # Fetch affected record to return current group_id
        rec_a = self.db.query(Record).filter(Record.id == pair.record_a_id).first()
        affected_group_id = rec_a.group_id if rec_a else None

        # Log audit event
        self.audit.log(
            review_id=review_id,
            actor=data.reviewer_name or actor,
            event_type="pair_decision_recorded",
            target_type="duplicate_pair",
            target_id=pair.id,
            before_state={"status": previous_status},
            after_state={
                "status": new_status,
                "decision": decision.decision,
                "affected_group_id": affected_group_id,
            },
            note=data.note,
        )

        return PairDecisionResult(
            status="recorded",
            decision_id=decision.id,
            duplicate_pair_id=pair.id,
            affected_group_id=affected_group_id,
        )

    def get_duplicate_pairs(
        self,
        review_id: str,
        tier: str | None = None,
        decided: bool | None = None,
    ) -> list[DuplicatePairResponse]:
        """Lists candidate duplicate pairs with side-by-side record summaries."""
        query = (
            self.db.query(DuplicatePair)
            .options(
                joinedload(DuplicatePair.record_a),
                joinedload(DuplicatePair.record_b),
                joinedload(DuplicatePair.decisions),
            )
            .filter(DuplicatePair.review_id == review_id)
        )

        if tier:
            query = query.filter(DuplicatePair.tier == tier)

        if decided is False:
            query = query.filter(DuplicatePair.status == "pending")
        elif decided is True:
            query = query.filter(DuplicatePair.status != "pending")

        pairs = query.order_by(DuplicatePair.similarity_score.desc()).all()

        results = []
        for p in pairs:
            rec_a_summary = RecordSummary.model_validate(p.record_a) if p.record_a else None
            rec_b_summary = RecordSummary.model_validate(p.record_b) if p.record_b else None
            dec_responses = [PairDecisionResponse.model_validate(d) for d in p.decisions]

            results.append(
                DuplicatePairResponse(
                    id=p.id,
                    review_id=p.review_id,
                    record_a_id=p.record_a_id,
                    record_b_id=p.record_b_id,
                    record_a=rec_a_summary,
                    record_b=rec_b_summary,
                    similarity_score=p.similarity_score,
                    tier=p.tier,
                    match_reasons=p.match_reasons,
                    status=p.status,
                    created_at=p.created_at,
                    decisions=dec_responses,
                )
            )

        return results

    def capture_group_snapshot(self, query_version_id: str) -> int:
        """Captures an immutable snapshot of group assignments for exact zero-API rollback (Scenario E)."""
        query_version = (
            self.db.query(QueryVersion).filter(QueryVersion.id == query_version_id).first()
        )
        if not query_version:
            raise NotFoundError(f"Query version '{query_version_id}' was not found.")

        # Find all records linked to this query version
        q_records = (
            self.db.query(Record)
            .join(QueryRecord, QueryRecord.record_id == Record.id)
            .filter(QueryRecord.query_version_id == query_version_id)
            .all()
        )

        count = 0
        for r in q_records:
            if not r.group_id:
                continue

            existing_snap = (
                self.db.query(GroupSnapshot)
                .filter(
                    GroupSnapshot.query_version_id == query_version_id,
                    GroupSnapshot.record_id == r.id,
                )
                .first()
            )

            if existing_snap:
                existing_snap.group_id = r.group_id
                existing_snap.is_representative = "true" if r.is_representative else "false"
            else:
                snap = GroupSnapshot(
                    query_version_id=query_version_id,
                    record_id=r.id,
                    group_id=r.group_id,
                    is_representative="true" if r.is_representative else "false",
                )
                self.db.add(snap)
            count += 1

        self.db.commit()
        return count
