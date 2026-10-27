import uuid

from backend.app.core.database import Base, utc_now
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship


class Record(Base):
    """Normalized bibliographic study stored idempotently.

    Never deleted. Records can only be hidden via state (is_hidden).
    """

    __tablename__ = "records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Provenance
    source = Column(String(50), nullable=False)  # 'europe_pmc' | 'pubmed'
    source_record_id = Column(String(100), nullable=False)

    # Identifiers
    doi = Column(String(255), nullable=True, index=True)
    pmid = Column(String(50), nullable=True, index=True)

    # Bibliographic content
    title = Column(Text, nullable=False)
    authors = Column(JSON, nullable=False, default=list)
    journal = Column(String(500), nullable=True)
    publication_year = Column(Integer, nullable=True, index=True)
    abstract = Column(Text, nullable=True)
    mesh_headings = Column(JSON, nullable=False, default=list)
    publication_types = Column(JSON, nullable=False, default=list)
    language = Column(String(20), nullable=True, default="eng")

    # Cluster grouping & state
    group_id = Column(
        String(36), ForeignKey("dedup_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_representative = Column(Boolean, nullable=False, default=False)
    is_hidden = Column(Boolean, nullable=False, default=False)

    # Raw metadata preserved for auditability
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    review = relationship("Review", back_populates="records")
    queries = relationship("QueryRecord", back_populates="record", cascade="all, delete-orphan")
    dedup_group = relationship("DedupGroup", back_populates="members", foreign_keys=[group_id])
    suggestions = relationship(
        "ScreeningSuggestion", back_populates="record", cascade="all, delete-orphan"
    )
    decisions = relationship(
        "ScreeningDecision", back_populates="record", cascade="all, delete-orphan"
    )
    pico_annotations = relationship(
        "PICOAnnotation", back_populates="record", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Non-negotiable idempotency key: (review_id, source, source_record_id)
        UniqueConstraint(
            "review_id", "source", "source_record_id", name="uq_record_review_source_id"
        ),
        Index("idx_record_title_year", "title", "publication_year"),
    )
