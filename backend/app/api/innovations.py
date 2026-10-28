"""Review suggestions and study family candidate endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.innovation_service import changed_criteria, study_families

router = APIRouter(tags=["Review intelligence"])


@router.get("/reviews/{review_id}/recheck-candidates")
def get_recheck_candidates(review_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return changed_criteria(db, review_id)


@router.get("/reviews/{review_id}/study-families")
def get_study_families(review_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return study_families(db, review_id)
