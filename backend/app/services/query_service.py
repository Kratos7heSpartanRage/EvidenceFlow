"""Query Strategy and Evolution service handling version trees, previews, and diffing."""

from typing import Any

from sqlalchemy.orm import Session

from app.adapters.base import SourceError
from app.core.database import utc_now
from app.core.errors import AppError, NotFoundError, ValidationError
from app.models.audit import PipelineRun, RunStep
from app.models.query import QueryRecord, QueryVersion
from app.models.record import Record
from app.repositories.query_repo import QueryRepository
from app.repositories.review_repo import ReviewRepository
from app.schemas.contracts import QuerySpec, RecordIn
from app.schemas.query import (
    QueryCreate,
    QueryDiffResponse,
    QueryImportResponse,
    QueryPreviewResponse,
    QueryResponse,
    QueryRevertResponse,
)
from app.services.audit_service import AuditService
from app.services.source_service import source_adapter


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
            synonyms=data.spec.expand_synonyms,
            title_abstract_only=data.spec.title_abstract_only,
            date_from=data.spec.date_from.isoformat() if data.spec.date_from else None,
            date_to=data.spec.date_to.isoformat() if data.spec.date_to else None,
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

        if query.preview_payload is not None:
            return QueryPreviewResponse.model_validate(query.preview_payload)
        if sample_records is not None and estimated_hits is not None:
            samples, est_hits, warnings = sample_records, estimated_hits, []
        else:
            spec = QuerySpec(
                source=query.source,
                expression=query.expression,
                expand_synonyms=query.synonyms,
                title_abstract_only=query.title_abstract_only,
                date_from=query.date_from,
                date_to=query.date_to,
                language=query.language,
            )
            try:
                preview = source_adapter(query.source).preview(spec, n=20)
            except SourceError as exc:
                raise AppError(
                    exc.message,
                    code="SOURCE_ERROR",
                    status_code=502,
                    details={"source": exc.source, "kind": exc.kind},
                ) from exc
            samples = [record.model_dump(mode="json") for record in preview.records]
            est_hits, warnings = preview.hit_count, preview.warnings
        response = QueryPreviewResponse(
            query_id=query.id,
            estimated_hits=est_hits,
            sample_records=samples,
            is_frozen=True,
            warnings=warnings,
        )
        if query.status == "draft":
            query.status = "previewed"
            query.frozen_at = utc_now()
            query.hit_count = est_hits
            query.preview_payload = response.model_dump(mode="json")
            self.db.commit()
            self.audit.log(
                review_id=query.review_id,
                actor=actor,
                event_type="query_previewed",
                target_type="query_version",
                target_id=query.id,
                before_state={"status": "draft"},
                after_state={"status": "previewed", "hit_count": est_hits},
            )
        return response

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
        if existing_run and existing_run.status in ("running", "completed", "awaiting_processing"):
            return QueryImportResponse(run_id=existing_run.id, status=existing_run.status)

        if records_in is None:
            raise AppError(
                "The background import processor is not connected yet.",
                code="PIPELINE_NOT_READY",
                status_code=501,
            )
        if query.status == "draft":
            raise ValidationError("Preview and approve this query before importing records.")
        expected_source = query.source
        if any(record.source.value != expected_source for record in records_in):
            raise ValidationError("Every imported record must use the query's literature source.")

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
        if records_in is not None:
            # Batch preload existing records and links to eliminate N+1 DB queries
            existing_records = {
                (r[0], r[1]): r[2]
                for r in self.db.query(Record.source, Record.source_record_id, Record.id)
                .filter(Record.review_id == query.review_id)
                .all()
            }
            existing_links = {
                qr[0]
                for qr in self.db.query(QueryRecord.record_id)
                .filter(QueryRecord.query_version_id == query.id)
                .all()
            }

            imported_count = 0
            for r_in in records_in:
                src_val = r_in.source.value if hasattr(r_in.source, "value") else str(r_in.source)
                rec_key = (src_val, r_in.source_record_id)

                if rec_key in existing_records:
                    rec_id = existing_records[rec_key]
                else:
                    new_rec = Record(
                        review_id=query.review_id,
                        source=src_val,
                        source_record_id=r_in.source_record_id,
                        doi=r_in.doi,
                        pmid=r_in.pmid,
                        title=r_in.title,
                        authors=[author.model_dump(mode="json") for author in r_in.authors],
                        journal=r_in.journal,
                        publication_year=r_in.publication_year,
                        abstract=r_in.abstract,
                        mesh_headings=r_in.mesh_headings,
                        publication_types=r_in.publication_types,
                        language=r_in.language,
                        raw_payload={
                            "source_payload": r_in.raw,
                            "normalized": r_in.model_dump(mode="json", exclude={"raw"}),
                        },
                    )
                    self.db.add(new_rec)
                    self.db.flush()
                    rec_id = new_rec.id
                    existing_records[rec_key] = rec_id
                    imported_count += 1

                # Link record to this query version idempotently
                if rec_id not in existing_links:
                    qr = QueryRecord(query_version_id=query.id, record_id=rec_id)
                    self.db.add(qr)
                    existing_links.add(rec_id)

            query.imported_count = (query.imported_count or 0) + imported_count
            # Fetch/store is a completed step. Commit it before deduplication,
            # so a later failure preserves the imported records and provenance.
            steps[0].status = "completed"
            steps[0].completed_at = utc_now()
            run.progress_percent = 25
            run.current_step = "deduplicate"
            self.db.commit()
            from app.services.deduplication_db_service import DatabaseDeduplicationService

            try:
                dedup_service = DatabaseDeduplicationService(self.db)
                steps[1].status = "running"
                steps[1].started_at = utc_now()
                dedup_service.score_current_records(query.review_id)
                dedup_service.cluster_records(query.review_id, commit=False)
                dedup_service.capture_group_snapshot(query.id, commit=False)
                steps[1].status = "completed"
                steps[1].completed_at = utc_now()
            except Exception as exc:
                self.db.rollback()
                run.status = "failed"
                run.error_message = (
                    "Deduplication failed; imported records remain available for retry."
                )
                run.current_step = "deduplicate"
                run.completed_at = utc_now()
                steps[1].status = "failed"
                steps[1].completed_at = utc_now()
                steps[1].message = run.error_message
                self.db.commit()
                raise AppError(run.error_message, code="DEDUPLICATION_FAILED") from exc
            run.status = "awaiting_processing"
            run.progress_percent = 50
            run.current_step = "screen_heuristics"
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

    def revert_query(self, query_id: str, actor: str = "Reviewer") -> QueryRevertResponse:
        """Exact, zero-API revert (Scenario E).

        Restores workspace to the exact state captured in GroupSnapshot at the completion
        of query_id. Records present in snapshot are unhidden and restored to snapshot groups;
        records not present in snapshot are soft-hidden. ZERO external calls are made.
        """
        query = self.query_repo.get(query_id)
        if not query:
            raise NotFoundError(f"Query version '{query_id}' was not found.")

        # Load snapshots for target query version
        from app.models.dedup import GroupSnapshot

        snapshots = (
            self.db.query(GroupSnapshot).filter(GroupSnapshot.query_version_id == query_id).all()
        )
        if not snapshots:
            raise ValidationError(
                f"Cannot revert to query '{query_id}': no group snapshot exists for this query version."
            )

        # Build fast O(1) lookup dictionary for snapshot records
        snapshot_by_record = {s.record_id: s for s in snapshots}

        # Fetch all records in this review
        records = self.db.query(Record).filter(Record.review_id == query.review_id).all()

        restored_count = 0
        hidden_count = 0

        for r in records:
            if r.id in snapshot_by_record:
                snap = snapshot_by_record[r.id]
                r.is_hidden = False
                r.group_id = snap.group_id
                r.is_representative = str(snap.is_representative).lower() == "true"
                restored_count += 1
            else:
                r.is_hidden = True
                hidden_count += 1

        # Audit event
        self.audit.log(
            review_id=query.review_id,
            actor=actor,
            event_type="query_reverted",
            target_type="query_version",
            target_id=query.id,
            before_state=None,
            after_state={
                "restored_version_id": query.id,
                "version_number": query.version_number,
                "restored_records_count": restored_count,
                "hidden_records_count": hidden_count,
            },
            note=f"Zero-API rollback to Query v{query.version_number} ({query.label})",
        )

        self.db.commit()
        return QueryRevertResponse(
            status="reverted",
            restored_version_id=query.id,
            restored_records_count=restored_count,
            hidden_records_count=hidden_count,
        )
