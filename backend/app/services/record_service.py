"""Record query service providing filtered, paginated record lists and full detail projections."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models.query import QueryRecord
from app.models.record import Record
from app.models.screening import ScreeningDecision
from app.schemas.record import (
    PicoSpanItem,
    RecordDecisionSummary,
    RecordDetailResponse,
    RecordItem,
    RecordListResponse,
    RecordSuggestionSummary,
)
from app.services.pico_annotation_service import effective_pico_annotations


class RecordService:
    def __init__(self, db: Session):
        self.db = db

    def list_records(
        self,
        review_id: str,
        status: str | None = None,
        decision: str | None = None,
        q: str | None = None,
        version_id: str | None = None,
        representatives_only: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> RecordListResponse:
        """Efficiently queries and filters records for a review."""
        page = max(1, page)
        page_size = max(1, min(page_size, 500))

        query = self.db.query(Record).filter(Record.review_id == review_id)

        # Soft deletion filtering
        if status == "hidden":
            query = query.filter(Record.is_hidden.is_(True))
        elif status == "all":
            pass
        else:
            query = query.filter(Record.is_hidden.is_(False))

        # Representatives filter
        if representatives_only:
            query = query.filter(Record.is_representative.is_(True))

        # Query version filter via junction
        if version_id:
            query = query.join(QueryRecord, QueryRecord.record_id == Record.id).filter(
                QueryRecord.query_version_id == version_id
            )

        # Search visible bibliographic text and source identifiers.
        if q and q.strip():
            search_term = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    Record.title.ilike(search_term),
                    Record.abstract.ilike(search_term),
                    Record.pmid.ilike(search_term),
                    Record.source_record_id.ilike(search_term),
                )
            )

        # Decision filter pushed down to database level using index
        if decision:
            if decision == "unscreened":
                active_dec_subq = (
                    self.db.query(ScreeningDecision.id)
                    .filter(
                        ScreeningDecision.record_id == Record.id,
                        ScreeningDecision.superseded_by_id.is_(None),
                    )
                    .exists()
                )
                query = query.filter(~active_dec_subq)
            elif decision in ("include", "exclude", "maybe"):
                query = query.join(
                    ScreeningDecision,
                    (ScreeningDecision.record_id == Record.id)
                    & (ScreeningDecision.superseded_by_id.is_(None)),
                ).filter(ScreeningDecision.decision == decision)

        query = query.distinct()
        total_count = query.count()

        # Eager load relationships via selectinload to prevent Cartesian multiplication
        records = (
            query.options(
                selectinload(Record.decisions),
                selectinload(Record.suggestions),
            )
            .order_by(Record.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items: list[RecordItem] = []
        for r in records:
            # Pick latest human decision
            active_decision = None
            if r.decisions:
                unsuperseded = [d for d in r.decisions if d.superseded_by_id is None]
                if unsuperseded:
                    latest_dec = max(unsuperseded, key=lambda d: d.created_at)
                    active_decision = RecordDecisionSummary.model_validate(latest_dec)

            # Pick latest machine suggestion
            active_suggestion = None
            if r.suggestions:
                latest_sug = max(r.suggestions, key=lambda s: s.created_at)
                active_suggestion = RecordSuggestionSummary.model_validate(latest_sug)

            items.append(
                RecordItem(
                    id=r.id,
                    review_id=r.review_id,
                    source=r.source,
                    source_record_id=r.source_record_id,
                    title=r.title,
                    authors=r.authors or [],
                    journal=r.journal,
                    publication_year=r.publication_year,
                    doi=r.doi,
                    pmid=r.pmid,
                    group_id=r.group_id,
                    is_representative=r.is_representative,
                    is_hidden=r.is_hidden,
                    decision=active_decision,
                    suggestion=active_suggestion,
                )
            )

        return RecordListResponse(
            items=items,
            total=total_count,
            page=page,
            page_size=page_size,
        )

    def get_record(self, record_id: str) -> RecordDetailResponse:
        """Fetches full bibliographic record details with decisions, suggestions, PICO, and cluster members."""
        record = (
            self.db.query(Record)
            .populate_existing()
            .options(
                selectinload(Record.decisions),
                selectinload(Record.suggestions),
                selectinload(Record.pico_annotations),
            )
            .filter(Record.id == record_id)
            .first()
        )
        if not record:
            raise NotFoundError(f"Record '{record_id}' was not found.")

        # Latest human decision
        decisions_sorted = sorted(record.decisions, key=lambda d: d.created_at, reverse=True)
        active_decision = (
            RecordDecisionSummary.model_validate(decisions_sorted[0]) if decisions_sorted else None
        )

        # Latest machine suggestion
        suggestions_sorted = sorted(record.suggestions, key=lambda s: s.created_at, reverse=True)
        active_suggestion = (
            RecordSuggestionSummary.model_validate(suggestions_sorted[0])
            if suggestions_sorted
            else None
        )

        # PICO Spans
        pico_spans = [
            PicoSpanItem.model_validate(p)
            for p in sorted(
                effective_pico_annotations(record.pico_annotations),
                key=lambda p: p.start_index or 0,
            )
        ]

        # Sibling cluster members
        cluster_members: list[RecordItem] = []
        if record.group_id:
            siblings = (
                self.db.query(Record)
                .filter(Record.group_id == record.group_id, Record.id != record.id)
                .all()
            )
            for sib in siblings:
                cluster_members.append(
                    RecordItem(
                        id=sib.id,
                        review_id=sib.review_id,
                        source=sib.source,
                        source_record_id=sib.source_record_id,
                        title=sib.title,
                        authors=sib.authors or [],
                        journal=sib.journal,
                        publication_year=sib.publication_year,
                        doi=sib.doi,
                        pmid=sib.pmid,
                        group_id=sib.group_id,
                        is_representative=sib.is_representative,
                        is_hidden=sib.is_hidden,
                    )
                )

        return RecordDetailResponse(
            id=record.id,
            review_id=record.review_id,
            source=record.source,
            source_record_id=record.source_record_id,
            title=record.title,
            authors=record.authors or [],
            journal=record.journal,
            publication_year=record.publication_year,
            doi=record.doi,
            pmid=record.pmid,
            group_id=record.group_id,
            is_representative=record.is_representative,
            is_hidden=record.is_hidden,
            abstract=record.abstract,
            mesh_headings=record.mesh_headings or [],
            publication_types=record.publication_types or [],
            language=record.language,
            decision=active_decision,
            suggestion=active_suggestion,
            decisions=[RecordDecisionSummary.model_validate(d) for d in decisions_sorted],
            suggestions=[RecordSuggestionSummary.model_validate(s) for s in suggestions_sorted],
            pico_spans=pico_spans,
            pico_history=[PicoSpanItem.model_validate(p) for p in record.pico_annotations],
            cluster_members=cluster_members,
        )
