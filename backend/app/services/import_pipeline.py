"""Live import pipeline: source search -> store -> deduplicate -> screen -> PICO.

`POST /api/queries/{id}/import` creates a queued run (`start`) and executes it in
a background task (`run_import_in_background` -> `execute`). Every step commits
on its own, so a failure keeps earlier work, marks the run failed, and a new
import request retries it without duplicating anything:

- fetch_records: the adapter skips records this review already stores
  (`known_ids`), new records are saved with a SHA-256 content hash, and EVERY
  id the search returned, old or new, is linked to the query version. The
  links are what lets a later version show "already present" records and keep
  their earlier decisions.
- deduplicate: same database service and snapshot as the direct import path.
- screen_heuristics: machine suggestions for visible representatives, keyed by
  (record content, PICO terms, criteria, algorithm), so reruns add nothing new.
- pico_extract: machine spans for representatives not excluded by a reviewer
  (or, when undecided, by the machine suggestion).

Machine output never touches the human decision tables.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.adapters.base import SourceError
from app.core.config import settings
from app.core.database import SessionLocal, utc_now
from app.engines.pico import extract_pico
from app.engines.screening import ALGO_VERSION as SCREENING_ALGO_VERSION
from app.engines.screening import screen
from app.engines.types import CriterionSpec, PicoTerms, fingerprint
from app.models.audit import AuditEvent, PipelineRun, RunStep
from app.models.pico import PICOAnnotation
from app.models.query import QueryRecord, QueryVersion
from app.models.record import Record
from app.models.review import CriteriaVersion, Criterion, Review
from app.models.screening import ScreeningDecision, ScreeningSuggestion
from app.schemas.contracts import QuerySpec, RecordIn
from app.services.record_mapping import to_engine_record
from app.services.source_service import source_adapter

logger = logging.getLogger(__name__)

SYSTEM_ACTOR = "System Pipeline"
STEP_NAMES = ("fetch_records", "deduplicate", "screen_heuristics", "pico_extract")
STEP_PROGRESS = {
    "fetch_records": 25,
    "deduplicate": 50,
    "screen_heuristics": 75,
    "pico_extract": 100,
}

# Engine criterion codes a reviewer can name in `detector_rule`.
ENGINE_CRITERION_CODES = frozenset({"non_human", "non_english", "case_report", "simulation"})

# The schema requires a numeric confidence, but the screening engine returns a
# categorical strength, not a calibrated probability. Store the category as a
# fixed ordinal and keep the real strength in the evidence.
STRENGTH_ORDINAL = {"strong": 1.0, "weak": 0.5, "none": 0.0}

MAX_STEP_MESSAGE = 500
MAX_AUDITED_WARNINGS = 20


class StepFailed(Exception):
    """A pipeline step failed with a message that is safe to show the reviewer."""


# ---------------------------------------------------------------------- mapping


def record_content_hash(record: RecordIn) -> str:
    """SHA-256 of the bibliographic content (not the raw payload or ids)."""
    return fingerprint(
        {
            "title": record.title,
            "abstract": record.abstract,
            "authors": [author.full_name for author in record.authors],
            "doi": record.doi,
            "pmid": record.pmid,
            "year": record.year,
            "journal": record.journal,
            "language": record.language,
            "pub_types": list(record.pub_types),
            "mesh": list(record.mesh_terms),
        }
    )


def query_spec(query: QueryVersion) -> QuerySpec:
    return QuerySpec(
        source=query.source,
        expression=query.expression,
        expand_synonyms=query.synonyms,
        title_abstract_only=query.title_abstract_only,
        date_from=query.date_from,
        date_to=query.date_to,
        language=query.language,
    )


def criterion_specs(criteria: Iterable[Criterion]) -> list[CriterionSpec]:
    """Map stored criteria to the screening engine's input.

    `detector_rule` decides the detector; labels are never parsed:
    - an engine code (non_human, non_english, case_report, simulation) uses
      metadata first, then the engine's documented rule;
    - any other rule is read as alternative keywords separated by "|"
      (e.g. "rats|mice|murine") and matched in the title and abstract;
    - no rule means the reviewer applies the criterion, so the engine skips it.
    """
    specs: list[CriterionSpec] = []
    for criterion in criteria:
        rule = (criterion.detector_rule or "").strip()
        if not rule:
            continue
        kind = "include" if criterion.type == "inclusion" else "exclude"
        reason = (criterion.description or criterion.label or "").strip() or "Reviewer criterion"
        code = rule.lower()
        if code in ENGINE_CRITERION_CODES:
            specs.append(CriterionSpec(criterion.id, code, kind=kind, reason=reason))
            continue
        terms = [term.strip() for term in rule.split("|") if term.strip()]
        if terms:
            specs.append(
                CriterionSpec(
                    criterion.id,
                    "custom_keyword",
                    kind=kind,
                    reason=reason,
                    detector="rule",
                    params={"terms": terms},
                )
            )
    return specs


_PICO_KEYS = {
    "population": ("population", "P", "p"),
    "intervention": ("intervention", "I", "i"),
    "comparator": ("comparator", "comparison", "C", "c"),
    "outcome": ("outcome", "outcomes", "O", "o"),
}


def _split_terms(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    values = value if isinstance(value, (list, tuple)) else [value]
    terms: list[str] = []
    for item in values:
        terms.extend(part.strip() for part in re.split(r"[;,\n]", str(item)) if part.strip())
    return tuple(terms)


def pico_terms(pico: dict[str, Any] | None) -> PicoTerms:
    """Review PICO text to engine terms. Accepts full names or P/I/C/O keys; each
    field may list several terms separated by commas or semicolons."""
    pico = pico or {}
    values = {}
    for name, keys in _PICO_KEYS.items():
        found = next((pico[key] for key in keys if pico.get(key)), None)
        values[name] = _split_terms(found)
    return PicoTerms(**values)


def _record_row(review_id: str, record: RecordIn) -> Record:
    return Record(
        review_id=review_id,
        source=record.source.value,
        source_record_id=record.source_record_id,
        doi=record.doi,
        pmid=record.pmid,
        title=record.title,
        authors=[author.model_dump(mode="json") for author in record.authors],
        journal=record.journal,
        publication_year=record.year,
        abstract=record.abstract,
        mesh_headings=list(record.mesh_terms),
        publication_types=list(record.pub_types),
        language=record.language,
        raw_payload={
            "source_payload": record.raw,
            "normalized": record.model_dump(mode="json", exclude={"raw"}),
            "content_hash": record_content_hash(record),
        },
    )


def _evidence_json(suggestion) -> list[dict[str, Any]]:
    items = [
        {
            "code": item.code,
            "source": item.source,
            "field": item.field,
            "matched": list(item.matched),
            "explanation": item.explanation,
            "criterion_id": item.criterion_id,
        }
        for item in suggestion.evidence
    ]
    items.append({"code": "strength", "strength": suggestion.strength})
    return items


def _truncate(text: str, limit: int = MAX_STEP_MESSAGE) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


# --------------------------------------------------------------------- pipeline


class ImportPipeline:
    def __init__(
        self,
        db: Session,
        adapter_factory: Callable[[str], Any] | None = None,
        cap: int | None = None,
    ):
        self.db = db
        # Looked up at call time so tests can monkeypatch `source_adapter`.
        self._adapter_factory = adapter_factory
        self.cap = cap or settings.IMPORT_CAP

    def _adapter(self, source: str):
        if self._adapter_factory is not None:
            return self._adapter_factory(source)
        return source_adapter(source)

    # ------------------------------------------------------------- lifecycle

    def start(self, query: QueryVersion, actor: str = "Reviewer") -> PipelineRun:
        """Approve the query and create a queued run with its four steps."""
        previous_status = query.status
        query.status = "approved"
        run = PipelineRun(
            review_id=query.review_id,
            query_version_id=query.id,
            run_type="import",
            status="queued",
            progress_percent=0,
            current_step=STEP_NAMES[0],
        )
        self.db.add(run)
        self.db.flush()
        self.db.add_all(
            RunStep(run_id=run.id, step_order=order, name=name, status="queued")
            for order, name in enumerate(STEP_NAMES, start=1)
        )
        self.db.add(
            AuditEvent(
                review_id=query.review_id,
                actor=actor,
                event_type="query_imported",
                target_type="query_version",
                target_id=query.id,
                before_state={"status": previous_status},
                after_state={"status": "approved", "run_id": run.id, "mode": "live"},
            )
        )
        self.db.commit()
        return run

    def execute(self, run_id: str) -> PipelineRun:
        run = self.db.get(PipelineRun, run_id)
        if run is None:
            raise ValueError(f"Pipeline run '{run_id}' was not found.")
        query = self.db.get(QueryVersion, run.query_version_id)
        steps = {step.name: step for step in run.steps}
        run.status = "running"
        self.db.commit()

        summary: dict[str, Any] = {}
        for name in STEP_NAMES:
            step = steps[name]
            if step.status == "completed":
                continue
            step.status, step.started_at, step.message = "running", utc_now(), None
            run.current_step = name
            self.db.commit()
            try:
                message = getattr(self, f"_step_{name}")(run, query, summary)
            except Exception as exc:  # every failure must be recorded on the run
                self.db.rollback()
                if isinstance(exc, (StepFailed, SourceError)):
                    reason = exc.message if isinstance(exc, SourceError) else str(exc)
                else:
                    logger.exception("Import step %s failed for run %s", name, run.id)
                    reason = f"Unexpected error: {exc.__class__.__name__}"
                run = self.db.get(PipelineRun, run_id)
                step = next(item for item in run.steps if item.name == name)
                step.status, step.completed_at = "failed", utc_now()
                step.message = _truncate(f"{name} failed: {reason}")
                run.status, run.completed_at = "failed", utc_now()
                run.error_message = _truncate(
                    f"{name} failed: {reason}. Earlier steps were kept; import again to retry."
                )
                self.db.commit()
                return run
            step.status, step.completed_at = "completed", utc_now()
            step.message = _truncate(message)
            run.progress_percent = STEP_PROGRESS[name]
            self.db.commit()

        run.status, run.completed_at, run.current_step = "completed", utc_now(), None
        self.db.add(
            AuditEvent(
                review_id=run.review_id,
                actor=SYSTEM_ACTOR,
                event_type="import_pipeline_completed",
                target_type="query_version",
                target_id=query.id,
                before_state=None,
                after_state={"run_id": run.id, **summary},
            )
        )
        self.db.commit()
        return run

    # ----------------------------------------------------------------- steps

    def _step_fetch_records(self, run, query, summary) -> str:
        review_id = query.review_id
        known = dict(
            self.db.query(Record.source_record_id, Record.id)
            .filter(Record.review_id == review_id, Record.source == query.source)
            .all()
        )
        result = self._adapter(query.source).search(
            query_spec(query), cap=self.cap, known_ids=frozenset(known)
        )

        new_records = 0
        for record in result.records:
            if record.source_record_id in known:
                continue
            row = _record_row(review_id, record)
            self.db.add(row)
            self.db.flush()
            known[record.source_record_id] = row.id
            new_records += 1

        linked = {
            row[0]
            for row in self.db.query(QueryRecord.record_id)
            .filter(QueryRecord.query_version_id == query.id)
            .all()
        }
        unresolved = []
        for source_record_id in result.ids:
            record_id = known.get(source_record_id)
            if record_id is None:
                unresolved.append(source_record_id)
                continue
            if record_id not in linked:
                self.db.add(QueryRecord(query_version_id=query.id, record_id=record_id))
                linked.add(record_id)

        warnings = list(result.warnings)
        if unresolved:
            warnings.append(f"{len(unresolved)} returned id(s) had no usable record")
        query.hit_count = result.hit_count
        query.imported_count = len(linked)
        summary.update(
            hit_count=result.hit_count,
            retrieved=len(result.ids),
            new_records=new_records,
            already_stored=result.skipped_known,
            linked_to_version=len(linked),
            truncated=result.truncated,
            import_cap=self.cap,
            warnings=warnings[:MAX_AUDITED_WARNINGS],
            warning_count=len(warnings),
        )
        message = (
            f"{result.hit_count} hits; retrieved {len(result.ids)}"
            f"{f' (cap {self.cap})' if result.truncated else ''}; {new_records} new, "
            f"{result.skipped_known} already stored; {len(linked)} linked to this version"
        )
        if warnings:
            message += f"; {len(warnings)} warning(s): {warnings[0]}"
        return message

    def _step_deduplicate(self, run, query, summary) -> str:
        from app.services.deduplication_db_service import DatabaseDeduplicationService

        service = DatabaseDeduplicationService(self.db)
        service.score_current_records(query.review_id)
        service.cluster_records(query.review_id, commit=False)
        snapshot_rows = service.capture_group_snapshot(query.id, commit=False)
        summary["snapshot_rows"] = snapshot_rows
        return "Duplicate candidates scored and groups rebuilt"

    def _representatives(self, review_id: str) -> list[Record]:
        return (
            self.db.query(Record)
            .filter(
                Record.review_id == review_id,
                Record.is_hidden.is_(False),
                or_(Record.is_representative.is_(True), Record.group_id.is_(None)),
            )
            .order_by(Record.id)
            .all()
        )

    def _active_criteria_version(self, review_id: str) -> CriteriaVersion | None:
        return (
            self.db.query(CriteriaVersion)
            .filter(CriteriaVersion.review_id == review_id)
            .order_by(CriteriaVersion.version_number.desc())
            .first()
        )

    def _step_screen_heuristics(self, run, query, summary) -> str:
        review = self.db.get(Review, query.review_id)
        version = self._active_criteria_version(review.id)
        criteria = list(version.criteria) if version else []
        labels = {criterion.id: criterion.label for criterion in criteria}
        specs = criterion_specs(criteria)
        terms = pico_terms(review.pico)
        context_hash = fingerprint(
            {"terms": terms.input_hash, "criteria": [spec.serializable() for spec in specs]}
        )
        version_id = version.id if version else None
        existing = {
            (record_id, content_hash)
            for record_id, content_hash in self.db.query(
                ScreeningSuggestion.record_id, ScreeningSuggestion.content_hash
            )
            .filter(
                ScreeningSuggestion.criteria_version_id == version_id
                if version_id
                else ScreeningSuggestion.criteria_version_id.is_(None),
                ScreeningSuggestion.algo_version == SCREENING_ALGO_VERSION,
            )
            .all()
        }

        created = counted = 0
        for record in self._representatives(review.id):
            counted += 1
            lite = to_engine_record(record)
            key = fingerprint({"record": lite.input_hash, "context": context_hash})
            if (record.id, key) in existing:
                continue
            suggestion = screen(lite, specs, terms)
            self.db.add(
                ScreeningSuggestion(
                    record_id=record.id,
                    criteria_version_id=version_id,
                    suggested_decision=suggestion.decision,
                    confidence=STRENGTH_ORDINAL[suggestion.strength],
                    matched_criterion_id=suggestion.criterion_id,
                    matched_criterion_label=labels.get(suggestion.criterion_id),
                    evidence_snippets=_evidence_json(suggestion),
                    content_hash=key,
                    algo_version=suggestion.algo_version,
                )
            )
            existing.add((record.id, key))
            created += 1
        summary.update(screened=counted, new_suggestions=created, engine_criteria=len(specs))
        return (
            f"{created} new suggestion(s) for {counted} study record(s); "
            f"{len(specs)} of {len(criteria)} criteria have a machine detector"
        )

    def _current_decision(self, record_id: str) -> str | None:
        decision = (
            self.db.query(ScreeningDecision.decision)
            .filter(
                ScreeningDecision.record_id == record_id,
                ScreeningDecision.superseded_by_id.is_(None),
            )
            .order_by(ScreeningDecision.created_at.desc())
            .first()
        )
        return decision[0] if decision else None

    def _latest_suggestion(self, record_id: str) -> str | None:
        suggestion = (
            self.db.query(ScreeningSuggestion.suggested_decision)
            .filter(ScreeningSuggestion.record_id == record_id)
            .order_by(ScreeningSuggestion.created_at.desc())
            .first()
        )
        return suggestion[0] if suggestion else None

    def _step_pico_extract(self, run, query, summary) -> str:
        review = self.db.get(Review, query.review_id)
        terms = pico_terms(review.pico)
        already_tagged = {
            row[0]
            for row in self.db.query(PICOAnnotation.record_id)
            .filter(PICOAnnotation.origin == "machine")
            .distinct()
            .all()
        }
        tagged = spans_added = skipped_excluded = 0
        for record in self._representatives(review.id):
            if record.id in already_tagged:
                continue
            decision = self._current_decision(record.id) or self._latest_suggestion(record.id)
            if decision == "exclude":
                skipped_excluded += 1
                continue
            spans = [
                span
                for span in extract_pico(record.abstract, terms)
                if span.status == "suggested"
                and span.text
                and span.start_char is not None
                and span.end_char is not None
            ]
            for span in spans:
                self.db.add(
                    PICOAnnotation(
                        record_id=record.id,
                        element=span.label,
                        text=span.text[:500],
                        start_index=span.start_char,
                        end_index=span.end_char,
                        confidence=None,
                        origin="machine",
                    )
                )
            if spans:
                tagged += 1
                spans_added += len(spans)
        summary.update(pico_records=tagged, pico_spans=spans_added)
        return (
            f"{spans_added} span(s) on {tagged} record(s); "
            f"{skipped_excluded} excluded record(s) skipped"
        )


def run_import_in_background(run_id: str) -> None:
    """Background-task entry point with its own database session."""
    with SessionLocal() as db:
        try:
            ImportPipeline(db).execute(run_id)
        except Exception:  # a background task must never raise
            logger.exception("Import pipeline crashed for run %s", run_id)
