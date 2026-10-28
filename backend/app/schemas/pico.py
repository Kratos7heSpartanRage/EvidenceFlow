"""PICO entity span request and response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PicoOp(BaseModel):
    """Single PICO annotation curation operation."""

    op: Literal["confirm", "correct", "reject"]
    span_id: str = Field(..., description="Target annotation ID")
    text: str | None = Field(default=None, description="Corrected entity text when op is 'correct'")
    start_index: int | None = Field(default=None, ge=0)
    end_index: int | None = Field(default=None, ge=0)


class PicoPatchIn(BaseModel):
    """Batch PICO curation payload."""

    ops: list[PicoOp] = Field(..., min_length=1, description="List of PICO curation operations")
    reviewer: str = Field(default="Human Reviewer", min_length=1)


class PicoPatchResponse(BaseModel):
    """Response confirming PICO span updates."""

    status: str = "updated"
    updated_count: int
