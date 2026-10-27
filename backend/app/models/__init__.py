"""SQLAlchemy ORM models package.

Exposes all Section 5 database entities for migration and application use.
"""

from backend.app.core.database import Base
from backend.app.models.audit import AuditEvent, PipelineRun, RunStep
from backend.app.models.dedup import DedupGroup, DuplicatePair, GroupSnapshot, PairDecision
from backend.app.models.loop import Conflict
from backend.app.models.pico import PICOAnnotation
from backend.app.models.query import QueryRecord, QueryVersion
from backend.app.models.record import Record
from backend.app.models.review import CriteriaVersion, Criterion, Review
from backend.app.models.screening import ScreeningDecision, ScreeningSuggestion

__all__ = [
    "AuditEvent",
    "Base",
    "Conflict",
    "CriteriaVersion",
    "Criterion",
    "DedupGroup",
    "DuplicatePair",
    "GroupSnapshot",
    "PICOAnnotation",
    "PairDecision",
    "PipelineRun",
    "QueryRecord",
    "QueryVersion",
    "Record",
    "Review",
    "RunStep",
    "ScreeningDecision",
    "ScreeningSuggestion",
]
