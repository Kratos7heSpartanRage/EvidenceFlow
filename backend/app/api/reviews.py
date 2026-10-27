"""Reviews and Criteria API endpoints."""

from backend.app.core.database import get_db
from backend.app.schemas.review import (
    CriteriaVersionCreate,
    CriteriaVersionResponse,
    ReviewCreate,
    ReviewListItem,
    ReviewResponse,
    ReviewUpdate,
)
from backend.app.services.review_service import ReviewService
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter(tags=["Reviews"])


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new systematic review",
)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    service = ReviewService(db)
    return service.create_review(payload)


@router.get("/reviews", response_model=list[ReviewListItem], summary="List all systematic reviews")
def list_reviews(db: Session = Depends(get_db)):
    service = ReviewService(db)
    return service.list_reviews()


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Get review details, metrics, and active criteria",
)
def get_review(review_id: str, db: Session = Depends(get_db)):
    service = ReviewService(db)
    return service.get_review(review_id)


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update review title, question, or PICO framework",
)
def update_review(review_id: str, payload: ReviewUpdate, db: Session = Depends(get_db)):
    service = ReviewService(db)
    return service.update_review(review_id, payload)


@router.post(
    "/reviews/{review_id}/criteria",
    response_model=CriteriaVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new immutable criteria version",
)
def create_criteria_version(
    review_id: str, payload: CriteriaVersionCreate, db: Session = Depends(get_db)
):
    service = ReviewService(db)
    return service.create_criteria_version(review_id, payload)


@router.get(
    "/reviews/{review_id}/criteria",
    response_model=CriteriaVersionResponse,
    summary="Get latest active criteria version",
)
def get_latest_criteria(review_id: str, db: Session = Depends(get_db)):
    service = ReviewService(db)
    review = service.get_review(review_id)
    return review.active_criteria_version
