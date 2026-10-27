"""Review and Criteria service orchestrating business rules and state."""

from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.models.review import CriteriaVersion, Criterion, Review
from backend.app.repositories.review_repo import ReviewRepository
from backend.app.schemas.review import (
    CriteriaVersionCreate,
    CriteriaVersionResponse,
    CriterionResponse,
    ReviewCreate,
    ReviewListItem,
    ReviewResponse,
    ReviewUpdate,
)
from backend.app.services.audit_service import AuditService
from sqlalchemy.orm import Session


class ReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReviewRepository(db)
        self.audit = AuditService(db)

    def create_review(self, data: ReviewCreate, actor: str = "Reviewer") -> ReviewResponse:
        review = Review(
            title=data.title,
            question=data.question,
            pico=data.pico or {},
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)

        # Handle initial criteria if supplied
        if data.initial_criteria:
            c_version = CriteriaVersion(
                review_id=review.id,
                version_number=1,
            )
            self.db.add(c_version)
            self.db.commit()
            self.db.refresh(c_version)

            for crit in data.initial_criteria:
                if crit.type not in ("inclusion", "exclusion"):
                    raise ValidationError(
                        f"Invalid criterion type '{crit.type}'. Must be 'inclusion' or 'exclusion'."
                    )
                criterion = Criterion(
                    criteria_version_id=c_version.id,
                    type=crit.type,
                    label=crit.label,
                    description=crit.description,
                    field_target=crit.field_target,
                    detector_rule=crit.detector_rule,
                )
                self.db.add(criterion)
            self.db.commit()

        # Log audit creation event
        self.audit.log(
            review_id=review.id,
            actor=actor,
            event_type="review_created",
            target_type="review",
            target_id=review.id,
            before_state=None,
            after_state={"title": review.title, "question": review.question, "pico": review.pico},
        )

        return self.repo.to_review_response(review)

    def get_review(self, review_id: str) -> ReviewResponse:
        review = self.repo.get(review_id)
        if not review:
            raise NotFoundError(f"Review '{review_id}' was not found.")
        return self.repo.to_review_response(review)

    def list_reviews(self) -> list[ReviewListItem]:
        reviews = self.repo.list_all()
        result = []
        for r in reviews:
            counts = self.repo.compute_counts(r.id)
            result.append(
                ReviewListItem(
                    id=r.id,
                    title=r.title,
                    question=r.question,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    counts=counts,
                )
            )
        return result

    def update_review(
        self, review_id: str, data: ReviewUpdate, actor: str = "Reviewer"
    ) -> ReviewResponse:
        review = self.repo.get(review_id)
        if not review:
            raise NotFoundError(f"Review '{review_id}' was not found.")

        before_state = {
            "title": review.title,
            "question": review.question,
            "pico": review.pico,
        }

        updated = False
        if data.title is not None and data.title != review.title:
            review.title = data.title
            updated = True
        if data.question is not None and data.question != review.question:
            review.question = data.question
            updated = True
        if data.pico is not None and data.pico != review.pico:
            review.pico = data.pico
            updated = True

        if updated:
            self.db.commit()
            self.db.refresh(review)
            after_state = {
                "title": review.title,
                "question": review.question,
                "pico": review.pico,
            }
            self.audit.log(
                review_id=review.id,
                actor=actor,
                event_type="review_updated",
                target_type="review",
                target_id=review.id,
                before_state=before_state,
                after_state=after_state,
            )

        return self.repo.to_review_response(review)

    def create_criteria_version(
        self, review_id: str, data: CriteriaVersionCreate, actor: str = "Reviewer"
    ) -> CriteriaVersionResponse:
        review = self.repo.get(review_id)
        if not review:
            raise NotFoundError(f"Review '{review_id}' was not found.")

        latest = self.repo.get_latest_criteria_version(review_id)
        next_ver = (latest.version_number + 1) if latest else 1

        new_version = CriteriaVersion(
            review_id=review_id,
            version_number=next_ver,
        )
        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)

        created_criteria = []
        for crit in data.criteria:
            if crit.type not in ("inclusion", "exclusion"):
                raise ValidationError(
                    f"Invalid criterion type '{crit.type}'. Must be 'inclusion' or 'exclusion'."
                )
            c = Criterion(
                criteria_version_id=new_version.id,
                type=crit.type,
                label=crit.label,
                description=crit.description,
                field_target=crit.field_target,
                detector_rule=crit.detector_rule,
            )
            self.db.add(c)
            created_criteria.append(c)
        self.db.commit()

        # Audit event
        self.audit.log(
            review_id=review_id,
            actor=actor,
            event_type="criteria_version_created",
            target_type="criteria_version",
            target_id=new_version.id,
            before_state={"previous_version": latest.version_number if latest else 0},
            after_state={"version_number": next_ver, "criteria_count": len(data.criteria)},
        )

        return CriteriaVersionResponse(
            id=new_version.id,
            review_id=new_version.review_id,
            version_number=new_version.version_number,
            created_at=new_version.created_at,
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
                for c in created_criteria
            ],
        )
