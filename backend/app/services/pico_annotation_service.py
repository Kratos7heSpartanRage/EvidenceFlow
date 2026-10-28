"""Append-only human PICO overlays; original machine rows are immutable."""

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.audit import AuditEvent
from app.models.pico import PICOAnnotation
from app.models.record import Record
from app.schemas.pico import PicoOp, PicoPatchResponse


def effective_pico_annotations(rows):
    superseded = {row.supersedes_id for row in rows if row.supersedes_id}
    by_id = {row.id: row for row in rows}
    leaves = [row for row in rows if row.id not in superseded]
    human = [row for row in leaves if row.origin == "human"]
    machines = [row for row in leaves if row.origin == "machine"]
    versioned = [row for row in machines if row.content_hash]
    if versioned:
        latest = max(versioned, key=lambda row: (row.created_at.replace(tzinfo=None), row.id))
        machines = [
            row
            for row in machines
            if (row.content_hash, row.algo_version) == (latest.content_hash, latest.algo_version)
        ]

    def key(row):
        return row.element, row.text, row.start_index, row.end_index

    suppressed = set()
    for row in human:
        original = row
        while original.supersedes_id and original.supersedes_id in by_id:
            original = by_id[original.supersedes_id]
        suppressed.add(key(original))
        suppressed.add(key(row))
    return [row for row in machines if key(row) not in suppressed] + [
        row for row in human if row.status != "rejected"
    ]


class PicoAnnotationService:
    def __init__(self, db: Session):
        self.db = db

    def patch_pico_annotations(
        self, record_id: str, ops: list[PicoOp], actor: str = "Human Reviewer"
    ) -> PicoPatchResponse:
        record = self.db.get(Record, record_id)
        if record is None:
            raise NotFoundError(f"Record '{record_id}' was not found.")
        rows = self.db.query(PICOAnnotation).filter_by(record_id=record_id).all()
        by_id = {row.id: row for row in rows}
        if any(op.span_id not in by_id for op in ops):
            raise NotFoundError("A target annotation was not found on this record.")
        children = {
            row.supersedes_id: row
            for row in sorted(rows, key=lambda row: (row.created_at.replace(tzinfo=None), row.id))
            if row.supersedes_id
        }
        applied = 0
        try:
            for op in ops:
                span = by_id[op.span_id]
                while span.id in children:
                    span = children[span.id]
                status = {"confirm": "confirmed", "correct": "corrected", "reject": "rejected"}[
                    op.op
                ]
                text = (op.text or "").strip() if op.op == "correct" else span.text
                if not text:
                    raise ValidationError("A corrected annotation requires nonempty text.")
                start, end = span.start_index, span.end_index
                if op.op != "reject":
                    abstract = record.abstract or ""
                    if op.start_index is not None:
                        start = op.start_index
                    elif abstract[start:end] != text:
                        start = abstract.find(text)
                        if start < 0 or abstract.find(text, start + 1) >= 0:
                            raise ValidationError(
                                "Corrected text must match an unambiguous abstract span; supply start_index for repeated text."
                            )
                    end = start + len(text)
                    if op.end_index is not None and op.end_index != end:
                        raise ValidationError("end_index does not match the selected text.")
                    if abstract[start:end] != text:
                        raise ValidationError(
                            "Annotation offsets must slice the exact abstract text."
                        )
                if span.origin == "human" and (
                    span.status,
                    span.text,
                    span.start_index,
                    span.end_index,
                ) == (status, text, start, end):
                    continue
                overlay = PICOAnnotation(
                    record_id=record_id,
                    element=span.element,
                    text=text,
                    start_index=start,
                    end_index=end,
                    confidence=None,
                    origin="human",
                    is_confirmed=op.op != "reject",
                    status=status,
                    supersedes_id=span.id,
                    reviewer=actor,
                    content_hash=span.content_hash,
                    algo_version=span.algo_version,
                )
                self.db.add(overlay)
                self.db.flush()
                children[span.id] = overlay
                by_id[overlay.id] = overlay
                applied += 1
            if applied:
                self.db.add(
                    AuditEvent(
                        review_id=record.review_id,
                        actor=actor,
                        event_type="pico_annotated",
                        target_type="record",
                        target_id=record_id,
                        after_state={
                            "applied_count": applied,
                            "ops": [op.model_dump() for op in ops],
                        },
                    )
                )
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return PicoPatchResponse(status="updated", updated_count=applied)
