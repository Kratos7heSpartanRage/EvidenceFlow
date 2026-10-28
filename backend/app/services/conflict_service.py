"""Conflict management service for tracking and resolving reviewer disagreements."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import utc_now
from app.core.errors import ConflictError, NotFoundError
from app.models.audit import AuditEvent
from app.models.loop import Conflict
from app.models.record import Record
from app.models.screening import ScreeningDecision
from app.schemas.conflict import ConflictResolveIn
from app.services.decision_service import validate_criterion_scope


class ConflictService:
    def __init__(self, db: Session):
        self.db = db

    def list_conflicts(self, review_id: str, status: str = "open") -> list[Conflict]:
        """Lists conflicts for a review filtered by status ('open', 'resolved', or 'all')."""
        query = self.db.query(Conflict).filter(Conflict.review_id == review_id)
        if status != "all":
            query = query.filter(Conflict.status == status)
        return query.order_by(Conflict.created_at.desc()).all()

    def resolve_conflict(
        self,
        conflict_id: str,
        data: ConflictResolveIn,
    ) -> tuple[Conflict, int]:
        """Resolves a human reviewer conflict by writing a consensus screening verdict

        to all cluster members with origin='conflict_resolution' and superseding prior decisions.
        """
        conflict = self.db.query(Conflict).filter(Conflict.id == conflict_id).first()
        if not conflict:
            raise NotFoundError(f"Conflict '{conflict_id}' was not found.")

        if conflict.status == "resolved":
            return conflict, 0
        if conflict.reason == "pair_override_bypassed":
            raise ConflictError(
                "Resolve structural conflicts through duplicate pair decisions before screening consensus."
            )
        validate_criterion_scope(self.db, conflict.review_id, data.criterion_id)

        # Find all records in the conflicting cluster
        records = (
            self.db.query(Record)
            .filter(
                Record.review_id == conflict.review_id,
                (Record.group_id == conflict.group_id) | (Record.id == conflict.group_id),
            )
            .all()
        )
        if not records:
            # Fallback if group_id is a single record id
            records = self.db.query(Record).filter(Record.id == conflict.group_id).all()

        record_ids = [r.id for r in records]

        # Fetch active decisions for cluster members to supersede them
        active_decisions = (
            self.db.query(ScreeningDecision)
            .filter(
                ScreeningDecision.record_id.in_(record_ids),
                ScreeningDecision.superseded_by_id.is_(None),
            )
            .all()
        )
        active_by_record = {}
        for decision in active_decisions:
            active_by_record.setdefault(decision.record_id, []).append(decision)

        # Apply consensus decision
        now = utc_now()
        for r in records:
            new_decision = ScreeningDecision(
                record_id=r.id,
                group_id=r.group_id,
                decision=data.decision,
                criterion_id=data.criterion_id,
                reason_text=data.reason_text,
                reviewer_name=data.reviewer,
                origin="conflict_resolution",
                note=data.note,
                created_at=now,
            )
            self.db.add(new_decision)
            self.db.flush()

            for prev in active_by_record.get(r.id, []):
                prev.superseded_by_id = new_decision.id

        # Update conflict status
        conflict.open_fingerprint = None
        conflict.status = "resolved"
        conflict.resolved_at = now
        conflict.resolved_by = data.reviewer
        if data.note:
            conflict.resolution_note = (
                f"{conflict.resolution_note or ''}\nResolution: {data.note}".strip()
            )

        # Log audit trail
        audit = AuditEvent(
            review_id=conflict.review_id,
            actor=data.reviewer,
            event_type="conflict_resolved",
            target_type="conflict",
            target_id=conflict.id,
            after_state={
                "status": "resolved",
                "consensus_decision": data.decision,
                "affected_records_count": len(records),
                "group_id": conflict.group_id,
            },
            note=data.note,
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(conflict)
        return conflict, len(records)
