"""PICO annotation service handling human curation, confirmations, corrections, and audit logging."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.audit import AuditEvent
from app.models.pico import PICOAnnotation
from app.models.record import Record
from app.schemas.pico import PicoOp, PicoPatchResponse


class PicoAnnotationService:
    def __init__(self, db: Session):
        self.db = db

    def patch_pico_annotations(
        self,
        record_id: str,
        ops: list[PicoOp],
        actor: str = "Human Reviewer",
    ) -> PicoPatchResponse:
        """Applies human confirmations, corrections, or rejections to extracted PICO spans.

        Maintains data integrity, never mutates raw provenance, and logs an append-only audit event.
        """
        record = self.db.query(Record).filter(Record.id == record_id).first()
        if not record:
            raise NotFoundError(f"Record '{record_id}' was not found.")

        target_ids = [op.span_id for op in ops]
        existing_spans = (
            self.db.query(PICOAnnotation)
            .filter(
                PICOAnnotation.id.in_(target_ids),
                PICOAnnotation.record_id == record_id,
            )
            .all()
        )
        spans_by_id = {span.id: span for span in existing_spans}

        applied_count = 0
        for op in ops:
            span = spans_by_id.get(op.span_id)
            if not span:
                continue

            if op.op == "confirm":
                span.is_confirmed = True
                span.origin = "human"
                applied_count += 1
            elif op.op == "correct":
                # Demote previous span and create corrected human annotation
                span.is_confirmed = False
                corrected_text = op.text.strip() if (op.text and op.text.strip()) else span.text
                corrected_span = PICOAnnotation(
                    record_id=record.id,
                    element=span.element,
                    text=corrected_text,
                    start_index=span.start_index,
                    end_index=span.start_index + len(corrected_text),
                    confidence=1.0,
                    origin="human",
                    is_confirmed=True,
                )
                self.db.add(corrected_span)
                applied_count += 1
            elif op.op == "reject":
                span.is_confirmed = False
                applied_count += 1

        if applied_count > 0:
            audit = AuditEvent(
                review_id=record.review_id,
                actor=actor,
                event_type="pico_annotated",
                target_type="record",
                target_id=record.id,
                after_state={
                    "applied_count": applied_count,
                    "ops": [op.model_dump() for op in ops],
                },
                note=f"Human curation of {applied_count} PICO entity span(s)",
            )
            self.db.add(audit)
            self.db.commit()

        return PicoPatchResponse(status="updated", updated_count=applied_count)
