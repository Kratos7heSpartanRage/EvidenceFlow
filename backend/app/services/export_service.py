"""Review export and audit trail services."""

from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session, joinedload

from app.core.errors import NotFoundError
from app.models.audit import AuditEvent
from app.models.loop import Conflict
from app.models.record import Record
from app.models.review import Review
from app.schemas.export import AuditEventResponse, AuditListResponse


class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def export_review_csv(self, review_id: str) -> tuple[str, bool]:
        """Generates RFC 4180 compliant CSV export containing included canonical study records.

        Quarantines records associated with open reviewer conflicts.
        Returns (csv_string, has_open_conflicts).
        """
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise NotFoundError(f"Review '{review_id}' was not found.")

        # Identify quarantined groups with open conflicts
        open_conflicts = (
            self.db.query(Conflict)
            .filter(Conflict.review_id == review_id, Conflict.status == "open")
            .all()
        )
        has_open_conflicts = len(open_conflicts) > 0
        quarantined_group_ids = {c.group_id for c in open_conflicts}

        # Query canonical, non-hidden representative records
        records = (
            self.db.query(Record)
            .options(joinedload(Record.decisions))
            .filter(
                Record.review_id == review_id,
                Record.is_hidden.is_(False),
                Record.is_representative.is_(True),
            )
            .order_by(Record.publication_year.desc().nullslast(), Record.created_at.asc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output, dialect="excel", lineterminator="\r\n")

        # RFC 4180 CSV Header
        headers = [
            "id",
            "source",
            "source_record_id",
            "doi",
            "pmid",
            "title",
            "authors",
            "journal",
            "publication_year",
            "abstract",
            "group_id",
            "decision",
            "reviewer_name",
            "decision_note",
        ]
        writer.writerow(headers)

        for rec in records:
            # Check quarantine status
            if rec.group_id in quarantined_group_ids or rec.id in quarantined_group_ids:
                continue

            # Check active human screening decision
            active_dec = None
            if rec.decisions:
                unsuperseded = [d for d in rec.decisions if d.superseded_by_id is None]
                if unsuperseded:
                    active_dec = max(unsuperseded, key=lambda d: d.created_at)

            # Only export studies with active 'include' verdict
            if not active_dec or active_dec.decision != "include":
                continue

            # Format authors list
            authors_str = ""
            if rec.authors:
                formatted_authors: list[str] = []
                for a in rec.authors:
                    if isinstance(a, dict):
                        formatted_authors.append(a.get("full_name") or a.get("last_name") or "")
                    else:
                        formatted_authors.append(str(a))
                authors_str = "; ".join(filter(None, formatted_authors))

            writer.writerow(
                [
                    rec.id,
                    rec.source,
                    rec.source_record_id,
                    rec.doi or "",
                    rec.pmid or "",
                    rec.title or "",
                    authors_str,
                    rec.journal or "",
                    rec.publication_year or "",
                    rec.abstract or "",
                    rec.group_id or "",
                    active_dec.decision,
                    active_dec.reviewer_name or "",
                    active_dec.note or "",
                ]
            )

        return output.getvalue(), has_open_conflicts

    def list_audit_events(
        self,
        review_id: str,
        page: int = 1,
        page_size: int = 50,
        event_type: str | None = None,
    ) -> AuditListResponse:
        """Returns paginated, chronologically ordered append-only audit events."""
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise NotFoundError(f"Review '{review_id}' was not found.")

        page = max(1, page)
        page_size = max(1, min(page_size, 500))

        query = self.db.query(AuditEvent).filter(AuditEvent.review_id == review_id)
        if event_type:
            query = query.filter(AuditEvent.event_type == event_type)

        total_count = query.count()
        events = (
            query.order_by(AuditEvent.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return AuditListResponse(
            items=[AuditEventResponse.model_validate(e) for e in events],
            total=total_count,
            page=page,
            page_size=page_size,
        )
