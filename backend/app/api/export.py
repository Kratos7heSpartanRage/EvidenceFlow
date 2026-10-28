"""Review CSV Export and Audit Ledger API endpoints."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.export import AuditListResponse
from app.services.export_service import ExportService

router = APIRouter(tags=["Export & Audit"])


@router.get(
    "/reviews/{review_id}/export.csv",
    status_code=status.HTTP_200_OK,
    summary="Export included canonical records as RFC 4180 CSV",
)
def export_review_csv(
    review_id: str,
    db: Session = Depends(get_db),
):
    """Exports all included canonical study records in RFC 4180 compliant CSV format.

    Quarantines records involved in open conflicts and sets X-Conflict-Warning header if conflicts exist.
    """
    service = ExportService(db)
    csv_content, has_conflicts = service.export_review_csv(review_id)

    headers = {
        "Content-Disposition": f"attachment; filename=review_{review_id}_included.csv",
        "Content-Type": "text/csv; charset=utf-8",
    }
    if has_conflicts:
        headers["X-Conflict-Warning"] = "QUARANTINE_OPEN_CONFLICTS"

    return Response(content=csv_content, media_type="text/csv; charset=utf-8", headers=headers)


@router.get(
    "/reviews/{review_id}/audit",
    response_model=AuditListResponse,
    status_code=status.HTTP_200_OK,
    summary="List audit ledger events for review",
)
def list_audit_events(
    review_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    event_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Returns paginated, immutable audit ledger history for the review."""
    service = ExportService(db)
    return service.list_audit_events(
        review_id=review_id,
        page=page,
        page_size=page_size,
        event_type=event_type,
    )
