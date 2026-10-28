"""Query repository for query versions, record lineage, and diff math."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.loop import Conflict
from app.models.query import QueryRecord, QueryVersion
from app.models.screening import ScreeningDecision
from app.schemas.query import QueryDiffResponse


class QueryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, query_id: str) -> QueryVersion | None:
        return self.db.query(QueryVersion).filter(QueryVersion.id == query_id).first()

    def list_for_review(self, review_id: str) -> list[QueryVersion]:
        return (
            self.db.query(QueryVersion)
            .filter(QueryVersion.review_id == review_id)
            .order_by(QueryVersion.version_number.asc())
            .all()
        )

    def get_next_version_number(self, review_id: str) -> int:
        highest = (
            self.db.query(func.max(QueryVersion.version_number))
            .filter(QueryVersion.review_id == review_id)
            .scalar()
        )
        return (highest or 0) + 1

    def get_record_ids(self, query_version_id: str) -> set[str]:
        rows = (
            self.db.query(QueryRecord.record_id)
            .filter(QueryRecord.query_version_id == query_version_id)
            .all()
        )
        return {r[0] for r in rows}

    def compute_diff(self, query_v2_id: str, query_v1_id: str) -> QueryDiffResponse:
        v1_records = self.get_record_ids(query_v1_id)
        v2_records = self.get_record_ids(query_v2_id)

        new_ids = v2_records - v1_records
        retained_ids = v2_records & v1_records
        dropped_ids = v1_records - v2_records

        already_screened = 0
        if retained_ids:
            # Query active screening decisions on retained records via SQL subquery (O(1) parameter overhead)
            v1_subquery = self.db.query(QueryRecord.record_id).filter(
                QueryRecord.query_version_id == query_v1_id
            )
            already_screened = (
                self.db.query(func.count(func.distinct(ScreeningDecision.record_id)))
                .join(QueryRecord, QueryRecord.record_id == ScreeningDecision.record_id)
                .filter(
                    QueryRecord.query_version_id == query_v2_id,
                    ScreeningDecision.superseded_by_id.is_(None),
                    QueryRecord.record_id.in_(v1_subquery),
                )
                .scalar()
                or 0
            )

        # Check potential conflicts among retained records
        potential_conflicts = 0
        q2 = self.get(query_v2_id)
        if q2:
            potential_conflicts = (
                self.db.query(func.count(Conflict.id))
                .filter(Conflict.review_id == q2.review_id, Conflict.status == "open")
                .scalar()
                or 0
            )

        return QueryDiffResponse(
            query_v1_id=query_v1_id,
            query_v2_id=query_v2_id,
            new_records_count=len(new_ids),
            retained_records_count=len(retained_ids),
            dropped_records_count=len(dropped_ids),
            already_screened_retained_count=already_screened,
            potential_conflicts_count=potential_conflicts,
        )
