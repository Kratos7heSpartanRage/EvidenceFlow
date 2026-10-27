import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base, utc_now


class DedupGroup(Base):
    """Cluster of records determined to represent the same underlying study."""

    __tablename__ = "dedup_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_record_id = Column(String(36), nullable=True)  # Elected representative record ID
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    members = relationship("Record", back_populates="dedup_group", foreign_keys="Record.group_id")


class DuplicatePair(Base):
    """Candidate duplicate pair scored by the deduplication engine."""

    __tablename__ = "duplicate_pairs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_a_id = Column(
        String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_b_id = Column(
        String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )

    similarity_score = Column(Float, nullable=False)
    tier = Column(
        String(50), nullable=False
    )  # tier_1_exact, tier_2_high_confidence, tier_3_review_needed
    match_reasons = Column(JSON, nullable=False, default=list)
    status = Column(
        String(30), nullable=False, default="pending"
    )  # pending, confirmed_duplicate, rejected_different
    created_at = Column(DateTime, nullable=False, default=utc_now)

    record_a = relationship("Record", foreign_keys=[record_a_id])
    record_b = relationship("Record", foreign_keys=[record_b_id])
    decisions = relationship(
        "PairDecision", back_populates="duplicate_pair", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "review_id", "record_a_id", "record_b_id", name="uq_duplicate_pair_canonical"
        ),
    )


class PairDecision(Base):
    """Human verdict on a candidate duplicate pair."""

    __tablename__ = "pair_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    duplicate_pair_id = Column(
        String(36), ForeignKey("duplicate_pairs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision = Column(String(30), nullable=False)  # 'confirm' | 'reject'
    reviewer_name = Column(String(255), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    duplicate_pair = relationship("DuplicatePair", back_populates="decisions")


class GroupSnapshot(Base):
    """Immutable snapshot of group assignments captured at the completion of a query run.

    Allows exact, zero-API-call restoration of historical review state upon revert.
    """

    __tablename__ = "group_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_version_id = Column(
        String(36), ForeignKey("query_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_id = Column(
        String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id = Column(String(36), nullable=False, index=True)
    is_representative = Column(String(10), nullable=False)  # 'true' | 'false'
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("query_version_id", "record_id", name="uq_snapshot_query_record"),
    )
