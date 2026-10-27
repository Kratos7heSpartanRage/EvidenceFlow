import uuid

from backend.app.core.database import Base, utc_now
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    question = Column(String(1000), nullable=False)
    pico = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    criteria_versions = relationship(
        "CriteriaVersion", back_populates="review", cascade="all, delete-orphan"
    )
    query_versions = relationship(
        "QueryVersion", back_populates="review", cascade="all, delete-orphan"
    )
    records = relationship("Record", back_populates="review", cascade="all, delete-orphan")


class CriteriaVersion(Base):
    __tablename__ = "criteria_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    review = relationship("Review", back_populates="criteria_versions")
    criteria = relationship(
        "Criterion", back_populates="criteria_version", cascade="all, delete-orphan"
    )


class Criterion(Base):
    __tablename__ = "criteria"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    criteria_version_id = Column(
        String(36),
        ForeignKey("criteria_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(20), nullable=False)  # 'inclusion' | 'exclusion'
    label = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    field_target = Column(String(50), nullable=True)  # 'title', 'abstract', 'mesh', etc.
    detector_rule = Column(String(500), nullable=True)  # Regex or heuristic pattern

    criteria_version = relationship("CriteriaVersion", back_populates="criteria")
