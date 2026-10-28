"""Review repository for database operations and aggregate metrics."""

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.loop import Conflict
from app.models.query import QueryVersion
from app.models.record import Record
from app.models.review import CriteriaVersion, Review
from app.models.screening import ScreeningDecision
from app.schemas.review import (
    CriteriaVersionResponse,
    CriterionResponse,
    ReviewCounts,
    ReviewResponse,
)


class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, review_id: str) -> Review | None:
        return self.db.query(Review).filter(Review.id == review_id).first()

    def list_all(self) -> list[Review]:
        return self.db.query(Review).order_by(Review.created_at.desc()).all()

    def get_latest_criteria_version(self, review_id: str) -> CriteriaVersion | None:
        return (
            self.db.query(CriteriaVersion)
            .options(joinedload(CriteriaVersion.criteria))
            .filter(CriteriaVersion.review_id == review_id)
            .order_by(CriteriaVersion.version_number.desc())
            .first()
        )

    def get_active_query(self, review_id: str) -> QueryVersion | None:
        # Active query is the most recent approved or previewed query
        return (
            self.db.query(QueryVersion)
            .filter(
                QueryVersion.review_id == review_id,
                QueryVersion.status.in_(["approved", "previewed", "draft"]),
            )
            .order_by(QueryVersion.version_number.desc())
            .first()
        )

    def compute_counts(self, review_id: str) -> ReviewCounts:
        # Total visible records
        total_records = (
            self.db.query(func.count(Record.id))
            .filter(Record.review_id == review_id, Record.is_hidden.is_(False))
            .scalar()
            or 0
        )

        # Unique studies: Count distinct groups or individual records in a single indexed pass
        unique_studies = (
            self.db.query(func.count(func.distinct(func.coalesce(Record.group_id, Record.id))))
            .filter(Record.review_id == review_id, Record.is_hidden.is_(False))
            .scalar()
            or 0
        )

        # Active (non-superseded) decisions for visible records
        active_decisions = (
            self.db.query(ScreeningDecision.decision, func.count(ScreeningDecision.id))
            .join(Record, Record.id == ScreeningDecision.record_id)
            .filter(
                Record.review_id == review_id,
                Record.is_hidden.is_(False),
                ScreeningDecision.superseded_by_id.is_(None),
            )
            .group_by(ScreeningDecision.decision)
            .all()
        )
        decision_map = {d: count for d, count in active_decisions}
        screened_included = decision_map.get("include", 0)
        screened_excluded = decision_map.get("exclude", 0)
        screened_maybe = decision_map.get("maybe", 0)
        unscreened = max(
            0, total_records - (screened_included + screened_excluded + screened_maybe)
        )

        # Open conflicts
        open_conflicts = (
            self.db.query(func.count(Conflict.id))
            .filter(Conflict.review_id == review_id, Conflict.status == "open")
            .scalar()
            or 0
        )

        return ReviewCounts(
            total_records=total_records,
            unique_studies=unique_studies,
            screened_included=screened_included,
            screened_excluded=screened_excluded,
            screened_maybe=screened_maybe,
            unscreened=unscreened,
            open_conflicts=open_conflicts,
        )

    def to_review_response(self, review: Review) -> ReviewResponse:
        counts = self.compute_counts(review.id)
        latest_c_ver = self.get_latest_criteria_version(review.id)
        active_query = self.get_active_query(review.id)

        active_criteria_dto = None
        if latest_c_ver:
            active_criteria_dto = CriteriaVersionResponse(
                id=latest_c_ver.id,
                review_id=latest_c_ver.review_id,
                version_number=latest_c_ver.version_number,
                created_at=latest_c_ver.created_at,
                criteria=[
                    CriterionResponse(
                        id=c.id,
                        criteria_version_id=c.criteria_version_id,
                        type=c.type,
                        label=c.label,
                        description=c.description,
                        field_target=c.field_target,
                        detector_rule=c.detector_rule,
                    )
                    for c in latest_c_ver.criteria
                ],
            )

        return ReviewResponse(
            id=review.id,
            title=review.title,
            question=review.question,
            pico=review.pico,
            created_at=review.created_at,
            updated_at=review.updated_at,
            counts=counts,
            active_criteria_version=active_criteria_dto,
            active_query_id=active_query.id if active_query else None,
        )
