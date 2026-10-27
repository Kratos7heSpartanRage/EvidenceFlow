import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base, utc_now


class ScreeningSuggestion(Base):
    """Machine-generated screening recommendation.

    Lives in a separate table from human decisions. Never mutates human tables.
    """

    __tablename__ = "screening_suggestions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = Column(
        String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criteria_version_id = Column(
        String(36),
        ForeignKey("criteria_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    suggested_decision = Column(String(20), nullable=False)  # 'include' | 'exclude' | 'maybe'
    confidence = Column(Float, nullable=False)
    matched_criterion_id = Column(
        String(36), ForeignKey("criteria.id", ondelete="SET NULL"), nullable=True
    )
    matched_criterion_label = Column(String(255), nullable=True)
    evidence_snippets = Column(JSON, nullable=False, default=list)

    # Idempotency tracking
    content_hash = Column(String(64), nullable=False)
    algo_version = Column(String(50), nullable=False, default="v1.0-rules")
    created_at = Column(DateTime, nullable=False, default=utc_now)

    record = relationship("Record", back_populates="suggestions")

    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "criteria_version_id",
            "content_hash",
            "algo_version",
            name="uq_suggestion_idempotency",
        ),
    )


class ScreeningDecision(Base):
    """Human-in-the-loop screening verdict.

    Append-only: previous decisions are superseded rather than updated in place.
    Enforces non-negotiable invariant: Every exclusion must have an explicit reason.
    """

    __tablename__ = "screening_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = Column(
        String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id = Column(String(36), nullable=True, index=True)

    decision = Column(String(20), nullable=False)  # 'include' | 'exclude' | 'maybe'
    criterion_id = Column(String(36), ForeignKey("criteria.id", ondelete="SET NULL"), nullable=True)
    reason_text = Column(String(500), nullable=True)
    reviewer_name = Column(String(255), nullable=False)
    origin = Column(
        String(50), nullable=False, default="human"
    )  # 'human' | 'inherited' | 'conflict_resolution'
    note = Column(Text, nullable=True)

    # Append-only lineage
    superseded_by_id = Column(String(36), ForeignKey("screening_decisions.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    record = relationship("Record", back_populates="decisions")
    superseded_by = relationship("ScreeningDecision", remote_side=[id])

    __table_args__ = (
        # Mandatory exclusion reason enforced directly in database schema
        CheckConstraint(
            "(decision != 'exclude') OR (criterion_id IS NOT NULL OR (reason_text IS NOT NULL AND length(trim(reason_text)) > 0))",
            name="chk_exclude_requires_reason",
        ),
        Index("idx_screening_decision_active", "record_id", "superseded_by_id"),
    )
