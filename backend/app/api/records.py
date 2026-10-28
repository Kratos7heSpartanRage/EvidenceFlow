"""Records API endpoints for bibliographic queries, search, and detail inspection."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.record import RecordDetailResponse, RecordListResponse
from app.services.record_service import RecordService

router = APIRouter(tags=["Records"])


@router.get(
    "/reviews/{review_id}/records",
    response_model=RecordListResponse,
    status_code=status.HTTP_200_OK,
    summary="List, search, and filter records for a review",
)
def list_records(
    review_id: str,
    status_filter: str | None = Query(
        default=None, alias="status", description="Record status: active, hidden, all"
    ),
    decision: str | None = Query(
        default=None, description="Screening decision: include, exclude, maybe, unscreened"
    ),
    q: str | None = Query(default=None, description="Search title, abstract, PMID, or source record ID"),
    version: str | None = Query(default=None, description="Query version ID filter"),
    representatives_only: bool = Query(
        default=True, description="Return only canonical cluster representatives"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db),
):
    service = RecordService(db)
    return service.list_records(
        review_id=review_id,
        status=status_filter,
        decision=decision,
        q=q,
        version_id=version,
        representatives_only=representatives_only,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/records/{record_id}",
    response_model=RecordDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full record details with provenance, decisions, suggestions, and PICO spans",
)
def get_record(
    record_id: str,
    db: Session = Depends(get_db),
):
    service = RecordService(db)
    return service.get_record(record_id)
