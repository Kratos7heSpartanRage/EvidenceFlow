import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base, utc_now


class PICOAnnotation(Base):
    """Extracted clinical PICO entity span."""

    __tablename__ = "pico_annotations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = Column(
        String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )

    element = Column(String(5), nullable=False)  # 'P' | 'I' | 'C' | 'O'
    text = Column(String(500), nullable=False)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=True)

    origin = Column(String(20), nullable=False, default="machine")  # 'machine' | 'human'
    is_confirmed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    record = relationship("Record", back_populates="pico_annotations")

    __table_args__ = (Index("idx_pico_record_element", "record_id", "element"),)
