"""Deduplication and Duplicate Pair API endpoints."""

from backend.app.core.database import get_db
from backend.app.schemas.dedup import (
    DuplicatePairResponse,
    PairDecisionIn,
    PairDecisionResult,
)
from backend.app.services.deduplication_service import DeduplicationService
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

router = APIRouter(tags=["Deduplication"])


@router.get(
    "/reviews/{review_id}/duplicate-pairs",
    response_model=list[DuplicatePairResponse],
    summary="List candidate duplicate pairs with bibliographic comparisons",
)
def list_duplicate_pairs(
    review_id: str,
    tier: str | None = Query(
        default=None,
        description="Filter by tier: tier_1_exact, tier_2_high_confidence, tier_3_review_needed",
    ),
    decided: bool | None = Query(
        default=None, description="Filter by decided status (false for pending review)"
    ),
    db: Session = Depends(get_db),
):
    service = DeduplicationService(db)
    return service.get_duplicate_pairs(review_id=review_id, tier=tier, decided=decided)


@router.post(
    "/reviews/{review_id}/pair-decisions",
    response_model=PairDecisionResult,
    status_code=status.HTTP_200_OK,
    summary="Record human decision (confirm duplicate or reject) and trigger cluster regrouping",
)
def record_pair_decision(
    review_id: str,
    payload: PairDecisionIn,
    db: Session = Depends(get_db),
):
    service = DeduplicationService(db)
    return service.record_pair_decision(review_id=review_id, data=payload)
