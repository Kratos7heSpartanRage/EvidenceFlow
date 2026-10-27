import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base, utc_now


class AuditEvent(Base):
    """Immutable, append-only ledger entry tracking all human and pipeline actions.

    Never updated or deleted.
    """

    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )

    actor = Column(String(255), nullable=False)  # Reviewer name or 'System Pipeline'
    event_type = Column(
        String(50), nullable=False
    )  # 'human_screening', 'query_created', 'revert', etc.
    target_type = Column(String(50), nullable=False)  # 'record', 'query_version', 'conflict', etc.
    target_id = Column(String(36), nullable=False, index=True)

    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    note = Column(Text, nullable=True)

    __table_args__ = (Index("idx_audit_review_timestamp", "review_id", "timestamp"),)


class PipelineRun(Base):
    """Background execution job tracking async ingestion, dedup, or screening."""

    __tablename__ = "pipeline_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_version_id = Column(
        String(36), ForeignKey("query_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    run_type = Column(
        String(50), nullable=False
    )  # 'import', 'criteria_change', 'workspace_update', 'regroup'
    status = Column(
        String(20), nullable=False, default="queued"
    )  # queued, running, completed, failed
    progress_percent = Column(Integer, nullable=False, default=0)
    current_step = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=False, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    steps = relationship(
        "RunStep", back_populates="run", cascade="all, delete-orphan", order_by="RunStep.step_order"
    )


class RunStep(Base):
    """Individual sub-step within a pipeline execution."""

    __tablename__ = "run_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(
        String(36), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    step_order = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(
        String(20), nullable=False, default="queued"
    )  # queued, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    message = Column(String(500), nullable=True)

    run = relationship("PipelineRun", back_populates="steps")
