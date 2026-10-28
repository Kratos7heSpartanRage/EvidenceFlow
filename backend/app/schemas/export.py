"""Audit event and Export schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditEventResponse(BaseModel):
    """Immutable audit ledger record response."""

    id: str
    review_id: str
    actor: str
    event_type: str
    target_type: str
    target_id: str
    timestamp: datetime
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditListResponse(BaseModel):
    """Paginated list of immutable audit ledger entries."""

    items: list[AuditEventResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
