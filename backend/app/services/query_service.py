"""Query Strategy and Evolution service handling version trees, previews, and diffing."""

from typing import Any

from backend.app.core.database import utc_now
from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.models.audit import PipelineRun, RunStep
from backend.app.models.query import QueryRecord, QueryVersion
from backend.app.models.record import Record
from backend.app.repositories.query_repo import QueryRepository
from backend.app.repositories.review_repo import ReviewRepository
from backend.app.schemas.contracts import RecordIn
from backend.app.schemas.query import (
    QueryCreate,
    QueryDiffResponse,
    QueryImportResponse,
    QueryPreviewResponse,
    QueryResponse,
)
from backend.app.services.audit_service import AuditService
from sqlalchemy.orm import Session


class QueryService:
    def __init__(self, db: Session):
        self.db = db
        self.query_repo = QueryRepository(db)
        self.review_repo = ReviewRepository(db)
        self.audit = AuditService(db)

    def create_query(
        self, review_id: str, data: QueryCreate, actor: str = "Reviewer"
    ) -> QueryResponse:
        review = self.review_repo.get(review_id)
        if not review:
            raise NotFoundError(f"Review '{review_id}' was not found.")

        parent = None
        if data.parent_id:
            parent = self.query_repo.get(data.parent_id)
            if not parent:
                raise NotFoundError(f"Parent query '{data.parent_id}' was not found.")
            if parent.review_id != review_id:
                raise ValidationError("Parent query must belong to the same review.")

        version_number = self.query_repo.get_next_version_number(review_id)

        query = QueryVersion(
            review_id=review_id,
            parent_id=data.parent_id,
            version_number=version_number,
            label=data.label,
            expression=data.spec.expression,
            source=data.spec.source.value
            if hasattr(data.spec.source, "value")
            else str(data.spec.source),
            synonyms=data.spec.synonyms,
            date_from=data.spec.date_from,
            date_to=data.spec.date_to,
            language=data.spec.language or "eng",
            status="draft",
        )
        self.db.add(query)
        self.db.commit()
        self.db.refresh(query)

        self.audit.log(
            review_id=review_id,
            actor=actor,
            event_type="query_created",
            target_type="query_version",
            target_id=query.id,
            before_state=None,
            after_state={
                "version_number": version_number,
                "label": query.label,
                "expression": query.expression,
                "source": query.source,
            },
        )

        return QueryResponse.model_validate(query)

    def get_query(self, query_id: str) -> QueryResponse:
        query = self.query_repo.get(query_id)
        if not query:
            raise NotFoundError(f"Query '{query_id}' was not found.")
        return QueryResponse.model_validate(query)

    def list_queries(self, review_id: str) -> list[QueryResponse]:
        queries = self.query_repo.list_for_review(review_id)
        return [QueryResponse.model_validate(q) for q in queries]

    def preview_query(
        self,
        query_id: str,
        sample_records: list[dict[str, Any]] | None = None,
        estimated_hits: int | None = None,
        actor: str = "Reviewer",
    ) -> QueryPreviewResponse:
        query = self.query_repo.get(query_id)
        if not query:
            raise NotFoundError(f"Query '{query_id}' was not found.")

        # Estimate hits and sample records if not explicitly supplied
        est_hits = estimated_hits if estimated_hits is not None else (query.hit_count or 42)
        samples = (
            sample_records
            if sample_records is not None
            else [
                {
                    "title": f"Sample hit for query: {query.expression[:50]}...",
                    "source": query.source,
                    "publication_year": 2023,
                }
            ]
        )

        # Freezing query version specification on preview
        if query.status == "draft":
            query.status = "previewed"
            query.frozen_at = utc_now()
            query.hit_count = est_hits
            self.db.commit()
            self.db.refresh(query)

            self.audit.log(
                review_id=query.review_id,
                actor=actor,
                event_type="query_previewed",
                target_type="query_version",
                target_id=query.id,
                before_state={"status": "draft"},
                after_state={"status": "previewed", "hit_count": est_hits},
            )

        return QueryPreviewResponse(
            query_id=query.id,
            estimated_hits=query.hit_count or est_hits,
            sample_records=samples,
            is_frozen=True,
        )

    def import_query(
        self,
        query_id: str,
        records_in: list[RecordIn] | None = None,
        actor: str = "Reviewer",
    ) -> QueryImportResponse:
        query = self.query_repo.get(query_id)
        if not query:
            raise NotFoundError(f"Query '{query_id}' was not found.")

        # Non-negotiable idempotency: Return existing run if already running or completed
        existing_run = (
            self.db.query(PipelineRun)
            .filter(PipelineRun.query_version_id == query_id)
            .order_by(PipelineRun.started_at.desc())
            .first()
        )
        if existing_run and existing_run.status in ("running", "completed"):
            return QueryImportResponse(run_id=existing_run.id, status=existing_run.status)

        # Transition query status to approved
        query.status = "approved"

        # Create background pipeline run
        run = PipelineRun(
            review_id=query.review_id,
            query_version_id=query.id,
            run_type="import",
            status="running",
            progress_percent=0,
            current_step="fetch_records",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        # Standard pipeline sub-steps
        steps = [
            RunStep(run_id=run.id, step_order=1, name="fetch_records", status="running"),
            RunStep(run_id=run.id, step_order=2, name="deduplicate", status="queued"),
            RunStep(run_id=run.id, step_order=3, name="screen_heuristics", status="queued"),
            RunStep(run_id=run.id, step_order=4, name="pico_extract", status="queued"),
        ]
        self.db.add_all(steps)
        self.db.commit()

        # If records are provided directly (e.g. from adapter or test fixture), persist them idempotently
        if records_in:
            imported_count = 0
            for r_in in records_in:
                # Check for existing record by idempotency key (review_id, source, source_record_id)
                existing = (
                    self.db.query(Record)
                    .filter(
                        Record.review_id == query.review_id,
                        Record.source
                        == (
                            r_in.source.value if hasattr(r_in.source, "value") else str(r_in.source)
                        ),
                        Record.source_record_id == r_in.source_record_id,
                    )
                    .first()
                )

                if existing:
                    rec_id = existing.id
                else:
                    new_rec = Record(
                        review_id=query.review_id,
                        source=r_in.source.value
                        if hasattr(r_in.source, "value")
                        else str(r_in.source),
                        source_record_id=r_in.source_record_id,
                        doi=r_in.doi,
                        pmid=r_in.pmid,
                        title=r_in.title,
                        authors=r_in.authors,
                        journal=r_in.journal,
                        publication_year=r_in.publication_year,
                        abstract=r_in.abstract,
                        mesh_headings=r_in.mesh_headings,
                        publication_types=r_in.publication_types,
                        language=r_in.language,
                        raw_payload=r_in.raw_payload,
                    )
                    self.db.add(new_rec)
                    self.db.flush()
                    rec_id = new_rec.id
                    imported_count += 1

                # Link record to this query version idempotently
                existing_link = (
                    self.db.query(QueryRecord)
                    .filter(
                        QueryRecord.query_version_id == query.id,
                        QueryRecord.record_id == rec_id,
                    )
                    .first()
                )
                if not existing_link:
                    qr = QueryRecord(query_version_id=query.id, record_id=rec_id)
                    self.db.add(qr)

            query.imported_count = (query.imported_count or 0) + imported_count
            run.status = "completed"
            run.progress_percent = 100
            run.completed_at = utc_now()
            steps[0].status = "completed"
            steps[0].completed_at = utc_now()
            self.db.commit()

        self.audit.log(
            review_id=query.review_id,
            actor=actor,
            event_type="query_imported",
            target_type="query_version",
            target_id=query.id,
            before_state={"status": "previewed"},
            after_state={"status": "approved", "run_id": run.id},
        )

        return QueryImportResponse(run_id=run.id, status=run.status)

    def compute_diff(self, query_id: str, against_id: str) -> QueryDiffResponse:
        q1 = self.query_repo.get(against_id)
        if not q1:
            raise NotFoundError(f"Base query '{against_id}' was not found.")
        q2 = self.query_repo.get(query_id)
        if not q2:
            raise NotFoundError(f"Target query '{query_id}' was not found.")

        if q1.review_id != q2.review_id:
            raise ValidationError("Compared queries must belong to the same review.")

        return self.query_repo.compute_diff(query_id, against_id)
