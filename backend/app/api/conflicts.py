"""Conflict resolution API endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.conflict import ConflictResolveIn, ConflictResolveResult, ConflictResponse
from app.services.conflict_service import ConflictService

router = APIRouter(tags=["Conflicts"])


@router.get(
    "/reviews/{review_id}/conflicts",
    response_model=list[ConflictResponse],
    summary="List conflicts for a review",
)
def list_conflicts(
    review_id: str,
    status_filter: str = Query(default="open", alias="status"),
    db: Session = Depends(get_db),
):
    """Lists reviewer conflicts or contradictions flagged in the query loop."""
    service = ConflictService(db)
    return service.list_conflicts(review_id, status=status_filter)


@router.post(
    "/conflicts/{conflict_id}/resolve",
    response_model=ConflictResolveResult,
    status_code=status.HTTP_200_OK,
    summary="Resolve a conflict by consensus",
)
def resolve_conflict(
    conflict_id: str,
    payload: ConflictResolveIn,
    db: Session = Depends(get_db),
):
    """Resolves a human reviewer conflict by applying consensus decision to all cluster records."""
    service = ConflictService(db)
    conflict, affected_count = service.resolve_conflict(conflict_id, payload)
    return ConflictResolveResult(
        status="resolved",
        conflict_id=conflict.id,
        affected_records_count=affected_count,
    )
