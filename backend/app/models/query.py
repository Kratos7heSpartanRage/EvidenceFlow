import uuid

from backend.app.core.database import Base, utc_now
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship


class QueryVersion(Base):
    __tablename__ = "query_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id = Column(String(36), ForeignKey("query_versions.id"), nullable=True, index=True)
    version_number = Column(Integer, nullable=False)
    label = Column(String(255), nullable=False)

    # Query Specification (frozen after preview)
    expression = Column(String(2000), nullable=False)
    source = Column(String(50), nullable=False)  # 'europe_pmc' | 'pubmed'
    synonyms = Column(Boolean, nullable=False, default=True)
    date_from = Column(String(10), nullable=True)
    date_to = Column(String(10), nullable=True)
    language = Column(String(10), nullable=True, default="eng")

    # State & Metrics
    status = Column(
        String(20), nullable=False, default="draft"
    )  # draft, previewed, approved, superseded, reverted
    hit_count = Column(Integer, nullable=True)
    imported_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    frozen_at = Column(DateTime, nullable=True)

    # Relationships
    review = relationship("Review", back_populates="query_versions")
    parent = relationship("QueryVersion", remote_side=[id])
    records = relationship(
        "QueryRecord", back_populates="query_version", cascade="all, delete-orphan"
    )


class QueryRecord(Base):
    """Associates a record with the specific query version that retrieved it.

    Composite primary key guarantees that a record is linked to a query version exactly once.
    """

    __tablename__ = "query_records"

    query_version_id = Column(
        String(36), ForeignKey("query_versions.id", ondelete="CASCADE"), primary_key=True
    )
    record_id = Column(String(36), ForeignKey("records.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime, nullable=False, default=utc_now)

    query_version = relationship("QueryVersion", back_populates="records")
    record = relationship("Record", back_populates="queries")

    __table_args__ = (Index("idx_query_record_reverse", "record_id", "query_version_id"),)
