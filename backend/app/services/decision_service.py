"""Human screening decisions: append history, preserve opposing reviewers, audit changes."""

from sqlalchemy.orm import Session

from app.core.database import utc_now
from app.core.errors import NotFoundError, ValidationError
from app.models.audit import AuditEvent
from app.models.loop import Conflict
from app.models.record import Record
from app.models.review import CriteriaVersion, Criterion
from app.models.screening import ScreeningDecision
from app.schemas.screening import ScreeningDecisionIn


def validate_criterion_scope(db, review_id, criterion_id):
    if (
        criterion_id
        and db.query(Criterion.id)
        .join(CriteriaVersion)
        .filter(Criterion.id == criterion_id, CriteriaVersion.review_id == review_id)
        .first()
        is None
    ):
        raise ValidationError("The selected criterion does not belong to this review.")


class DecisionService:
    def __init__(self, db: Session):
        self.db = db

    def record_screening_decision(
        self, record_id: str, data: ScreeningDecisionIn
    ) -> ScreeningDecision:
        record = self.db.get(Record, record_id)
        if record is None:
            raise NotFoundError(f"Record '{record_id}' was not found.")
        validate_criterion_scope(self.db, record.review_id, data.criterion_id)
        records = (
            self.db.query(Record)
            .filter(Record.review_id == record.review_id, Record.group_id == record.group_id)
            .all()
            if record.group_id
            else [record]
        )
        ids = [row.id for row in records]
        active = (
            self.db.query(ScreeningDecision)
            .filter(
                ScreeningDecision.record_id.in_(ids), ScreeningDecision.superseded_by_id.is_(None)
            )
            .all()
        )
        own = [
            row
            for row in active
            if row.record_id == record_id
            and row.reviewer_name == data.reviewer_name
            and row.origin != "inherited"
        ]
        previous = max(
            own, key=lambda row: (row.created_at.replace(tzinfo=None), row.id), default=None
        )
        payload = (data.decision, data.criterion_id, data.reason_text, data.note)
        if (
            previous
            and (previous.decision, previous.criterion_id, previous.reason_text, previous.note)
            == payload
            and all(any(row.record_id == item.id for row in active) for item in records)
        ):
            return previous
        opposed = [
            row
            for row in active
            if {row.decision, data.decision} == {"include", "exclude"}
            and (
                row.reviewer_name != data.reviewer_name
                or (row.record_id != record_id and row.origin == "human")
            )
        ]
        group_ref = record.group_id or record.id
        if opposed:
            key = f"{record.review_id}:{group_ref}:include_vs_exclude"
            if (
                self.db.query(Conflict).filter_by(open_fingerprint=key, status="open").first()
                is None
            ):
                self.db.add(
                    Conflict(
                        review_id=record.review_id,
                        group_id=group_ref,
                        reason="include_vs_exclude",
                        status="open",
                        open_fingerprint=key,
                        resolution_note="; ".join(
                            f"{row.reviewer_name}: {row.decision}; {data.reviewer_name}: {data.decision}"
                            for row in opposed
                        ),
                    )
                )
        primary = None
        try:
            for item in records:
                current = [row for row in active if row.record_id == item.id]
                if item.id != record_id and any(
                    row in opposed and row.origin == "human" for row in current
                ):
                    continue
                new = ScreeningDecision(
                    record_id=item.id,
                    group_id=item.group_id,
                    decision=data.decision,
                    criterion_id=data.criterion_id,
                    reason_text=data.reason_text,
                    reviewer_name=data.reviewer_name,
                    origin="human" if item.id == record_id else "inherited",
                    note=data.note
                    if item.id == record_id
                    else f"Inherited from human decision on record {record_id}",
                    created_at=utc_now(),
                )
                self.db.add(new)
                self.db.flush()
                for row in current:
                    if row.reviewer_name == data.reviewer_name:
                        row.superseded_by_id = new.id
                if item.id == record_id:
                    primary = new
            self.db.add(
                AuditEvent(
                    review_id=record.review_id,
                    actor=data.reviewer_name,
                    event_type="human_screening",
                    target_type="record",
                    target_id=record_id,
                    before_state={
                        "decision": previous.decision,
                        "criterion_id": previous.criterion_id,
                        "reason_text": previous.reason_text,
                    }
                    if previous
                    else None,
                    after_state={
                        "decision": data.decision,
                        "criterion_id": data.criterion_id,
                        "reason_text": data.reason_text,
                        "cluster_records_count": len(records),
                    },
                    note=data.note,
                )
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return primary
