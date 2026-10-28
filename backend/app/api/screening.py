"""Screening decision API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.screening import ScreeningDecisionIn, ScreeningDecisionResponse
from app.services.decision_service import DecisionService

router = APIRouter(tags=["Screening"])


@router.post(
    "/records/{record_id}/screening",
    response_model=ScreeningDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record human screening decision",
)
def record_screening_decision(
    record_id: str,
    payload: ScreeningDecisionIn,
    db: Session = Depends(get_db),
):
    """Records a human screening verdict for a record, propagates to cluster group,

    detects reviewer conflicts, and appends an immutable audit event.
    """
    service = DecisionService(db)
    return service.record_screening_decision(record_id, payload)
