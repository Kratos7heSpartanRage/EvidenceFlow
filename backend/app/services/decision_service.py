"""Screening Decision service managing human decisions, cluster propagation, conflict detection, and audit logging."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import utc_now
from app.core.errors import NotFoundError
from app.models.audit import AuditEvent
from app.models.loop import Conflict
from app.models.record import Record
from app.models.screening import ScreeningDecision
from app.schemas.screening import ScreeningDecisionIn


class DecisionService:
    def __init__(self, db: Session):
        self.db = db

    def record_screening_decision(
        self, record_id: str, data: ScreeningDecisionIn
    ) -> ScreeningDecision:
        """Records a human screening verdict, supersedes prior decisions append-only,

        propagates to sibling cluster members, detects reviewer conflicts, and logs an audit event.
        """
        record = self.db.query(Record).filter(Record.id == record_id).first()
        if not record:
            raise NotFoundError(f"Record '{record_id}' was not found.")

        # Determine all target records in the cluster
        if record.group_id:
            cluster_records = self.db.query(Record).filter(Record.group_id == record.group_id).all()
        else:
            cluster_records = [record]

        record_ids = [r.id for r in cluster_records]

        # Fetch all currently active decisions for these cluster records (single query)
        active_decisions = (
            self.db.query(ScreeningDecision)
            .filter(
                ScreeningDecision.record_id.in_(record_ids),
                ScreeningDecision.superseded_by_id.is_(None),
            )
            .all()
        )
        active_by_record = {d.record_id: d for d in active_decisions}

        primary_prev = active_by_record.get(record.id)

        # Conflict Detection:
        # Check if an opposing decision exists by a different reviewer
        has_opposing_decision = False
        opposing_reasons = []
        for prev in active_decisions:
            if prev.reviewer_name != data.reviewer_name and {prev.decision, data.decision} == {
                "include",
                "exclude",
            }:
                has_opposing_decision = True
                opposing_reasons.append(
                    f"Reviewer '{prev.reviewer_name}' decided '{prev.decision}', "
                    f"while '{data.reviewer_name}' decided '{data.decision}'."
                )

        if has_opposing_decision:
            group_ref = record.group_id or record.id
            fingerprint = f"{record.review_id}:{group_ref}:include_vs_exclude"
            existing_conflict = (
                self.db.query(Conflict)
                .filter(Conflict.open_fingerprint == fingerprint, Conflict.status == "open")
                .first()
            )
            if not existing_conflict:
                conflict = Conflict(
                    review_id=record.review_id,
                    group_id=group_ref,
                    reason="include_vs_exclude",
                    status="open",
                    open_fingerprint=fingerprint,
                    resolution_note="; ".join(opposing_reasons),
                )
                self.db.add(conflict)

        # Create new decisions and supersede previous ones append-only
        created_decisions: list[ScreeningDecision] = []
        primary_decision: ScreeningDecision | None = None

        for rec in cluster_records:
            is_target = rec.id == record.id
            origin = "human" if is_target else "inherited"

            new_decision = ScreeningDecision(
                record_id=rec.id,
                group_id=rec.group_id,
                decision=data.decision,
                criterion_id=data.criterion_id,
                reason_text=data.reason_text,
                reviewer_name=data.reviewer_name,
                origin=origin,
                note=data.note
                if is_target
                else f"Inherited from human decision on record {record.id}",
                created_at=utc_now(),
            )
            self.db.add(new_decision)
            self.db.flush()  # generates new_decision.id

            prev = active_by_record.get(rec.id)
            if prev:
                prev.superseded_by_id = new_decision.id

            created_decisions.append(new_decision)
            if is_target:
                primary_decision = new_decision

        # Append-only Audit Trail
        audit_event = AuditEvent(
            review_id=record.review_id,
            actor=data.reviewer_name,
            event_type="human_screening",
            target_type="record",
            target_id=record.id,
            before_state=(
                {
                    "decision": primary_prev.decision,
                    "criterion_id": primary_prev.criterion_id,
                    "reason_text": primary_prev.reason_text,
                }
                if primary_prev
                else None
            ),
            after_state={
                "decision": data.decision,
                "criterion_id": data.criterion_id,
                "reason_text": data.reason_text,
                "cluster_records_count": len(cluster_records),
            },
            note=data.note,
        )
        self.db.add(audit_event)

        self.db.commit()
        if primary_decision:
            self.db.refresh(primary_decision)
            return primary_decision

        return created_decisions[0]
