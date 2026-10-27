import uuid

from backend.app.core.database import Base, utc_now
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text


class Conflict(Base):
    """Reviewer conflict or structural contradiction flagged in the query loop.

    Non-negotiable: Conflicts are never resolved automatically.
    """

    __tablename__ = "conflicts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id = Column(String(36), nullable=False, index=True)

    reason = Column(
        String(50), nullable=False
    )  # 'include_vs_exclude', 'pair_override_bypassed', etc.
    status = Column(String(20), nullable=False, default="open")  # 'open' | 'resolved'

    # Idempotency key: prevents duplicate open conflicts on query reruns
    open_fingerprint = Column(String(255), nullable=True, unique=True)

    created_at = Column(DateTime, nullable=False, default=utc_now)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolution_note = Column(Text, nullable=True)

    __table_args__ = (Index("idx_conflict_status_review", "review_id", "status"),)
