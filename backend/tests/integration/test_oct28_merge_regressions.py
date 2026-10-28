"""Boundary regressions for review APIs, pipeline retries, PICO and revert."""

import csv
import io

import pytest

from app.core.database import SessionLocal
from app.core.errors import NotFoundError, ValidationError
from app.models.audit import AuditEvent
from app.models.dedup import DuplicatePair, GroupSnapshot
from app.models.loop import Conflict
from app.models.pico import PICOAnnotation
from app.models.query import QueryRecord, QueryVersion
from app.models.record import Record
from app.models.review import CriteriaVersion, Criterion, Review
from app.models.screening import ScreeningSuggestion
from app.schemas.conflict import ConflictResolveIn
from app.schemas.contracts import RecordIn, SearchResult
from app.schemas.pico import PicoOp
from app.schemas.screening import ScreeningDecisionIn
from app.services.conflict_service import ConflictService
from app.services.decision_service import DecisionService
from app.services.deduplication_db_service import DatabaseDeduplicationService
from app.services.export_service import ExportService
from app.services.import_pipeline import ImportPipeline
from app.services.pico_annotation_service import PicoAnnotationService
from app.services.query_service import QueryService
from app.services.record_service import RecordService


@pytest.fixture
def context():
    with SessionLocal() as db:
        review = Review(
            title="October integration fixture",
            question="Does the workflow preserve evidence?",
            pico={"P": "patients", "I": "therapy"},
        )
        db.add(review)
        db.flush()
        record = Record(
            review_id=review.id,
            source="pubmed",
            source_record_id="1",
            title="Synthetic trial",
            abstract="Patients received therapy and placebo.",
            is_representative=True,
        )
        db.add(record)
        db.commit()
        yield db, review, record


def query(db, review):
    version = QueryVersion(
        review_id=review.id,
        version_number=db.query(QueryVersion).filter_by(review_id=review.id).count() + 1,
        label="Fixture search",
        expression="therapy",
        source="pubmed",
        status="previewed",
    )
    db.add(version)
    db.commit()
    return version


class Source:
    def __init__(self, records):
        self.records, self.calls = records, 0

    def search(self, spec, cap, known_ids=frozenset()):
        self.calls += 1
        return SearchResult(
            hit_count=len(self.records),
            ids=[r.source_record_id for r in self.records],
            records=[r for r in self.records if r.source_record_id not in known_ids],
        )


def test_pico_curation_appends_overlays_and_rejection_disappears(context):
    db, _, record = context
    original = PICOAnnotation(
        record_id=record.id,
        element="I",
        text="therapy",
        start_index=18,
        end_index=25,
        origin="machine",
        is_confirmed=False,
    )
    db.add(original)
    db.commit()
    service = PicoAnnotationService(db)
    service.patch_pico_annotations(record.id, [PicoOp(op="confirm", span_id=original.id)])
    assert original.origin == "machine" and original.is_confirmed is False
    assert RecordService(db).get_record(record.id).pico_spans[0].origin == "human"
    service.patch_pico_annotations(record.id, [PicoOp(op="reject", span_id=original.id)])
    detail = RecordService(db).get_record(record.id)
    assert detail.pico_spans == [] and len(detail.pico_history) == 3
    assert (
        service.patch_pico_annotations(
            record.id, [PicoOp(op="reject", span_id=original.id)]
        ).updated_count
        == 0
    )
    assert db.query(PICOAnnotation).filter_by(record_id=record.id).count() == 3


def test_pico_correction_offsets_slice_source_and_invalid_batch_is_atomic(context):
    db, _, record = context
    source = PICOAnnotation(
        record_id=record.id,
        element="I",
        text="therapy",
        start_index=18,
        end_index=25,
        origin="machine",
    )
    db.add(source)
    db.commit()
    service = PicoAnnotationService(db)
    service.patch_pico_annotations(
        record.id, [PicoOp(op="correct", span_id=source.id, text="therapy and placebo")]
    )
    span = RecordService(db).get_record(record.id).pico_spans[0]
    assert record.abstract[span.start_index : span.end_index] == span.text
    count = db.query(PICOAnnotation).filter_by(record_id=record.id).count()
    with pytest.raises(ValidationError):
        service.patch_pico_annotations(
            record.id,
            [
                PicoOp(op="confirm", span_id=source.id),
                PicoOp(op="correct", span_id=source.id, text="fabricated text"),
            ],
        )
    assert db.query(PICOAnnotation).filter_by(record_id=record.id).count() == count
    with pytest.raises(NotFoundError):
        service.patch_pico_annotations(
            record.id, [PicoOp(op="confirm", span_id="not-on-this-record")]
        )


def test_opposing_reviewers_remain_active_until_explicit_consensus(context):
    db, review, record = context
    service = DecisionService(db)
    first = service.record_screening_decision(
        record.id, ScreeningDecisionIn(decision="include", reviewer_name="A")
    )
    second = service.record_screening_decision(
        record.id,
        ScreeningDecisionIn(decision="exclude", reviewer_name="B", reason_text="Wrong population"),
    )
    assert first.superseded_by_id is None and second.superseded_by_id is None
    conflict = db.query(Conflict).filter_by(review_id=review.id, status="open").one()
    resolution = ConflictResolveIn(decision="maybe", reviewer="Consensus")
    ConflictService(db).resolve_conflict(conflict.id, resolution)
    assert first.superseded_by_id and second.superseded_by_id
    assert conflict.open_fingerprint is None
    count = db.query(AuditEvent).filter_by(review_id=review.id).count()
    assert ConflictService(db).resolve_conflict(conflict.id, resolution)[1] == 0
    assert db.query(AuditEvent).filter_by(review_id=review.id).count() == count
    service.record_screening_decision(
        record.id, ScreeningDecisionIn(decision="include", reviewer_name="C")
    )
    service.record_screening_decision(
        record.id,
        ScreeningDecisionIn(decision="exclude", reviewer_name="D", reason_text="New disagreement"),
    )
    assert db.query(Conflict).filter_by(review_id=review.id, status="open").count() == 1


def test_screening_noop_and_cross_review_criteria(context):
    db, _review, record = context
    service = DecisionService(db)
    payload = ScreeningDecisionIn(decision="include", reviewer_name="A")
    first = service.record_screening_decision(record.id, payload)
    assert service.record_screening_decision(record.id, payload).id == first.id
    other = Review(title="Other corpus", question="Other question")
    db.add(other)
    db.flush()
    version = CriteriaVersion(review_id=other.id, version_number=1)
    db.add(version)
    db.flush()
    criterion = Criterion(
        criteria_version_id=version.id,
        type="exclusion",
        label="Foreign",
        description="Other review's rule",
    )
    db.add(criterion)
    db.commit()
    with pytest.raises(ValidationError):
        service.record_screening_decision(
            record.id,
            ScreeningDecisionIn(decision="exclude", reviewer_name="A", criterion_id=criterion.id),
        )
    assert first.superseded_by_id is None


def test_completed_pipeline_cannot_execute_twice(context):
    db, review, _ = context
    version = query(db, review)
    source = Source([])
    pipeline = ImportPipeline(db, adapter_factory=lambda _: source)
    run = pipeline.start(version)
    assert pipeline.execute(run.id).status == "completed"
    assert pipeline.execute(run.id).status == "completed"
    assert source.calls == 1
    assert (
        db.query(AuditEvent)
        .filter_by(review_id=review.id, event_type="import_pipeline_completed")
        .count()
        == 1
    )


def test_empty_search_can_be_restored_without_external_calls(context):
    db, review, record = context
    version = query(db, review)
    source = Source([])
    pipeline = ImportPipeline(db, adapter_factory=lambda _: source)
    pipeline.execute(pipeline.start(version).id)
    assert version.snapshot_captured
    result = QueryService(db).revert_query(version.id)
    assert result.restored_records_count == 0 and record.is_hidden
    QueryService(db).revert_query(version.id)
    assert source.calls == 1
    assert (
        db.query(AuditEvent).filter_by(review_id=review.id, event_type="query_reverted").count()
        == 1
    )


def test_hidden_known_record_is_reactivated_and_linked(context):
    db, review, record = context
    record.is_hidden = True
    db.commit()
    version = query(db, review)
    source = Source(
        [RecordIn(source="pubmed", source_record_id=record.source_record_id, title=record.title)]
    )
    pipeline = ImportPipeline(db, adapter_factory=lambda _: source)
    assert pipeline.execute(pipeline.start(version).id).status == "completed"
    assert not record.is_hidden
    assert db.query(Record).filter_by(review_id=review.id).count() == 1
    assert db.query(QueryRecord).filter_by(query_version_id=version.id).count() == 1


def test_snapshot_elects_representative_inside_query_scope(context):
    db, review, record = context
    other = Record(
        review_id=review.id,
        source="europe_pmc",
        source_record_id="MED:1",
        title=record.title,
        doi="10.1000/shared",
    )
    record.doi = "10.1000/shared"
    db.add(other)
    db.commit()
    version = query(db, review)
    db.add(QueryRecord(query_version_id=version.id, record_id=other.id))
    db.commit()
    service = DatabaseDeduplicationService(db)
    service.score_current_records(review.id)
    service.cluster_records(review.id)
    service.capture_group_snapshot(version.id)
    snapshot = db.query(GroupSnapshot).filter_by(query_version_id=version.id).one()
    assert snapshot.is_representative == "true"
    QueryService(db).revert_query(version.id)
    assert other.is_representative and not other.is_hidden and record.is_hidden


def test_bad_source_record_rolls_back_fetch_step(context):
    db, review, _ = context
    version = query(db, review)
    source = Source(
        [RecordIn(source="europe_pmc", source_record_id="MED:bad", title="Wrong adapter")]
    )
    pipeline = ImportPipeline(db, adapter_factory=lambda _: source)
    assert pipeline.execute(pipeline.start(version).id).status == "failed"
    assert db.query(Record).filter_by(review_id=review.id, source_record_id="MED:bad").count() == 0


def test_manual_criterion_blocks_unearned_include_suggestion(context):
    db, review, record = context
    criteria = CriteriaVersion(review_id=review.id, version_number=1)
    db.add(criteria)
    db.flush()
    db.add(
        Criterion(
            criteria_version_id=criteria.id,
            type="inclusion",
            label="Adult participants",
            description="Reviewer checks age",
        )
    )
    db.commit()
    version = query(db, review)
    pipeline = ImportPipeline(db, adapter_factory=lambda _: Source([]))
    pipeline.execute(pipeline.start(version).id)
    assert (
        db.query(ScreeningSuggestion).filter_by(record_id=record.id).one().suggested_decision
        == "maybe"
    )


def test_merging_oppositely_screened_groups_creates_conflict_and_quarantines(context):
    db, review, first = context
    second = Record(
        review_id=review.id, source="pubmed", source_record_id="2", title="Another report"
    )
    db.add(second)
    db.commit()
    verdict = DecisionService(db)
    left = verdict.record_screening_decision(
        first.id, ScreeningDecisionIn(decision="include", reviewer_name="A")
    )
    right = verdict.record_screening_decision(
        second.id,
        ScreeningDecisionIn(decision="exclude", reviewer_name="B", reason_text="Wrong study"),
    )
    pair = DuplicatePair(
        review_id=review.id,
        record_a_id=min(first.id, second.id),
        record_b_id=max(first.id, second.id),
        similarity_score=1.0,
        tier="tier_1_exact",
    )
    db.add(pair)
    db.commit()
    DatabaseDeduplicationService(db).cluster_records(review.id)
    assert left.superseded_by_id is None and right.superseded_by_id is None
    assert db.query(Conflict).filter_by(review_id=review.id, status="open").count() == 1
    exported, warning = ExportService(db).export_review_csv(review.id)
    assert warning and list(csv.DictReader(io.StringIO(exported))) == []


def test_pico_retags_changed_review_terms_without_mutating_human_overlay(context):
    db, review, record = context
    pipeline = ImportPipeline(db, adapter_factory=lambda _: Source([]))
    first_query = query(db, review)
    pipeline.execute(pipeline.start(first_query).id)
    machine = db.query(PICOAnnotation).filter_by(record_id=record.id, origin="machine").all()
    assert machine
    original_ids = {row.id for row in machine}
    PicoAnnotationService(db).patch_pico_annotations(
        record.id, [PicoOp(op="confirm", span_id=machine[0].id)]
    )
    human = db.query(PICOAnnotation).filter_by(record_id=record.id, origin="human").one()
    review.pico = {"P": "patients", "I": "placebo"}
    db.commit()
    second_query = query(db, review)
    pipeline.execute(pipeline.start(second_query).id)
    all_machine = db.query(PICOAnnotation).filter_by(record_id=record.id, origin="machine").all()
    assert len(all_machine) > len(original_ids)
    assert original_ids <= {row.id for row in all_machine}
    assert human.id in {row.id for row in RecordService(db).get_record(record.id).pico_spans}
    assert human.origin == "human" and human.status == "confirmed"
