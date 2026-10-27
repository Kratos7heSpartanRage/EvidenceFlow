"""Audit service for creating append-only immutable audit trail entries."""

from typing import Any

from backend.app.models.audit import AuditEvent
from sqlalchemy.orm import Session


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        review_id: str,
        actor: str,
        event_type: str,
        target_type: str,
        target_id: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> AuditEvent:
        """Appends an immutable audit event to the ledger."""
        # Non-negotiable: zero audit events for no-op changes
        if before_state is not None and after_state is not None and before_state == after_state:
            return None

        event = AuditEvent(
            review_id=review_id,
            actor=actor,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            before_state=before_state,
            after_state=after_state,
            note=note,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
