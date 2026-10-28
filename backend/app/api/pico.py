"""PICO annotation curation API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pico import PicoPatchIn, PicoPatchResponse
from app.services.pico_annotation_service import PicoAnnotationService

router = APIRouter(tags=["PICO"])


@router.patch(
    "/records/{record_id}/pico",
    response_model=PicoPatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Curate PICO entity spans",
)
def patch_pico_annotations(
    record_id: str,
    payload: PicoPatchIn,
    db: Session = Depends(get_db),
):
    """Applies human confirmations, corrections, and rejections to PICO entity spans for a record."""
    service = PicoAnnotationService(db)
    return service.patch_pico_annotations(record_id, payload.ops, actor=payload.reviewer)
