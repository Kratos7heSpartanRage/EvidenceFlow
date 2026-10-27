"""Database regressions for integrating Phase 3 without breaking existing contracts."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.errors import AppError, ConflictError, ValidationError
from app.main import app
from app.models.audit import AuditEvent, PipelineRun
from app.models.dedup import DedupGroup, DuplicatePair, GroupSnapshot, PairDecision
from app.models.loop import Conflict
from app.models.query import QueryRecord, QueryVersion
from app.models.record import Record
from app.models.review import Review
from app.repositories.review_repo import ReviewRepository
from app.schemas.contracts import DuplicateTier, RecordIn, ScoredPair
from app.schemas.dedup import PairDecisionIn
from app.services.deduplication_db_service import DatabaseDeduplicationService
from app.services.query_service import QueryService


@pytest.fixture
def context():
    with SessionLocal() as db:
        review = Review(
            title="Dedup regression fixture", question="Does grouping preserve history?"
        )
        db.add(review)
        db.flush()
        records = [
            Record(
                review_id=review.id,
                source="pubmed",
                source_record_id=str(index),
                title=f"Synthetic study {index}",
                abstract="Patients received therapy.",
                authors=[{"full_name": "Smith J", "last_name": "Smith"}],
            )
            for index in range(3)
        ]
        db.add_all(records)
        db.commit()
        yield db, review, records, DatabaseDeduplicationService(db)


def candidate(a, b, score=1.0):
    return ScoredPair(
        a.id, b.id, score, DuplicateTier.TIER_1_EXACT, ["synthetic exact-match fixture"]
    )


def verdict(service, review, a, b, value):
    return service.record_pair_decision(
        review.id,
        PairDecisionIn(
            record_a_id=a.id,
            record_b_id=b.id,
            decision=value,
            reviewer_name="Fixture Reviewer",
        ),
    )


def test_reject_splits_existing_group_and_later_confirm_is_current(context):
    db, review, (a, b, _), service = context
    service.ingest_candidate_pairs(review.id, [candidate(a, b)])
    service.cluster_records(review.id)
    original = a.group_id
    assert a.group_id == b.group_id
    verdict(service, review, a, b, "reject")
    assert a.group_id != b.group_id
    assert db.get(DedupGroup, original) is not None  # historical group preserved
    verdict(service, review, a, b, "confirm")
    assert a.group_id == b.group_id == original
    assert (
        db.query(PairDecision)
        .join(DuplicatePair)
        .filter(DuplicatePair.review_id == review.id)
        .count()
        == 2
    )


def test_noop_verdict_does_not_append_decisions_or_audit(context):
    db, review, (a, b, _), service = context
    first = verdict(service, review, a, b, "confirm")
    second = verdict(service, review, a, b, "confirm")
    assert first.decision_id == second.decision_id
    assert (
        db.query(AuditEvent)
        .filter_by(review_id=review.id, event_type="pair_decision_recorded")
        .count()
        == 1
    )


def test_transitive_guard_is_stable_and_conflict_is_not_duplicated(context):
    db, review, (a, b, bridge), service = context
    verdict(service, review, a, b, "reject")
    service.ingest_candidate_pairs(review.id, [candidate(a, bridge), candidate(b, bridge)])
    service.cluster_records(review.id)
    initial = {record.id: record.group_id for record in (a, b, bridge)}
    for _ in range(3):
        service.cluster_records(review.id)
        assert {record.id: record.group_id for record in (a, b, bridge)} == initial
    assert a.group_id != b.group_id
    assert (
        db.query(Conflict)
        .filter_by(review_id=review.id, reason="pair_override_bypassed", status="open")
        .count()
        == 1
    )


def test_snapshot_remains_unchanged_after_rejection_and_recapture(context):
    db, review, (a, b, _), service = context
    query = QueryVersion(
        review_id=review.id, version_number=1, label="Fixture", expression="trial", source="pubmed"
    )
    db.add(query)
    db.flush()
    db.add_all([QueryRecord(query_version_id=query.id, record_id=record.id) for record in (a, b)])
    service.ingest_candidate_pairs(review.id, [candidate(a, b)])
    service.cluster_records(review.id)
    service.capture_group_snapshot(query.id)
    before = [
        (row.record_id, row.group_id, row.is_representative)
        for row in db.query(GroupSnapshot)
        .filter_by(query_version_id=query.id)
        .order_by(GroupSnapshot.record_id)
    ]
    verdict(service, review, a, b, "reject")
    service.capture_group_snapshot(query.id)
    after = [
        (row.record_id, row.group_id, row.is_representative)
        for row in db.query(GroupSnapshot)
        .filter_by(query_version_id=query.id)
        .order_by(GroupSnapshot.record_id)
    ]
    assert before == after
    assert a.group_id != b.group_id


def test_retained_historical_groups_do_not_inflate_dashboard(context):
    db, review, (a, b, _), service = context
    service.ingest_candidate_pairs(review.id, [candidate(a, b)])
    service.cluster_records(review.id)
    assert ReviewRepository(db).compute_counts(review.id).unique_studies == 2
    verdict(service, review, a, b, "reject")
    assert ReviewRepository(db).compute_counts(review.id).unique_studies == 3
    assert db.query(DedupGroup).filter_by(review_id=review.id).count() > 3


def test_cross_review_pair_is_rejected_before_writes(context):
    db, review, (a, b, _), service = context
    other = Review(title="Other review", question="Separate corpus")
    db.add(other)
    db.flush()
    outsider = Record(
        review_id=other.id, source="pubmed", source_record_id="outside", title="Outside"
    )
    db.add(outsider)
    db.commit()
    with pytest.raises(ValidationError):
        verdict(service, review, a, outsider, "confirm")
    with pytest.raises(ValidationError):
        service.ingest_candidate_pairs(review.id, [candidate(a, b), candidate(a, outsider)])
    assert db.query(DuplicatePair).filter_by(review_id=review.id).count() == 0


def test_changed_machine_evidence_is_rejected_without_overwrite(context):
    _db, review, (a, b, _), service = context
    initial = candidate(a, b)
    service.ingest_candidate_pairs(review.id, [initial])
    with pytest.raises(ConflictError, match="versioned evaluation"):
        service.ingest_candidate_pairs(review.id, [replace(initial, similarity_score=0.8)])
    assert _db.query(DuplicatePair).filter_by(review_id=review.id).one().similarity_score == 1.0


def test_repeated_pair_in_batch_is_stored_once(context):
    db, review, (a, b, _), service = context
    initial = candidate(a, b)
    service.ingest_candidate_pairs(
        review.id, [initial, replace(initial, record_a_id=b.id, record_b_id=a.id)]
    )
    assert db.query(DuplicatePair).filter_by(review_id=review.id).count() == 1


def test_verdict_and_regroup_roll_back_if_audit_fails(context, monkeypatch):
    db, review, (a, b, _), service = context
    service.ingest_candidate_pairs(review.id, [candidate(a, b)])
    service.cluster_records(review.id)
    before = a.group_id

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr("app.services.deduplication_db_service.AuditService.log", fail)
    with pytest.raises(RuntimeError, match="Synthetic audit failure"):
        verdict(service, review, a, b, "reject")
    assert a.group_id == b.group_id == before
    assert (
        db.query(PairDecision)
        .join(DuplicatePair)
        .filter(DuplicatePair.review_id == review.id)
        .count()
        == 0
    )


def test_duplicate_api_supports_structured_authors_and_rejects_bad_targets(context):
    _db, review, (a, b, _), service = context
    service.ingest_candidate_pairs(review.id, [candidate(a, b)])
    with TestClient(app) as client:
        response = client.get(f"/api/reviews/{review.id}/duplicate-pairs")
        assert response.status_code == 200
        assert response.json()[0]["record_a"]["authors"] == ["Smith J"]
        for payload in (
            {"decision": "confirm"},
            {"record_a_id": a.id, "record_b_id": a.id, "decision": "reject"},
        ):
            response = client.post(f"/api/reviews/{review.id}/pair-decisions", json=payload)
            assert response.status_code == 422


def test_dedup_failure_marks_run_failed_and_preserves_imported_records(context, monkeypatch):
    db, review, _, _ = context
    query = QueryVersion(
        review_id=review.id,
        version_number=1,
        label="Retry fixture",
        expression="trial",
        source="pubmed",
        status="previewed",
    )
    db.add(query)
    db.commit()

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic dedup failure")

    monkeypatch.setattr(DatabaseDeduplicationService, "cluster_records", fail)
    with pytest.raises(AppError, match="imported records remain"):
        QueryService(db).import_query(
            query.id,
            records_in=[
                RecordIn(
                    source="pubmed",
                    source_record_id="new-import",
                    title="Retry fixture record",
                )
            ],
        )
    run = db.query(PipelineRun).filter_by(query_version_id=query.id).one()
    assert run.status == "failed" and run.current_step == "deduplicate"
    assert run.progress_percent == 25 and run.completed_at is not None
    assert (
        db.query(Record).filter_by(review_id=review.id, source_record_id="new-import").count() == 1
    )
    assert db.query(QueryRecord).filter_by(query_version_id=query.id).count() == 1
    monkeypatch.undo()
    retry = QueryService(db).import_query(
        query.id,
        records_in=[
            RecordIn(
                source="pubmed",
                source_record_id="new-import",
                title="Retry fixture record",
            )
        ],
    )
    assert retry.run_id != run.id and retry.status == "awaiting_processing"
    assert (
        db.query(Record).filter_by(review_id=review.id, source_record_id="new-import").count() == 1
    )


def test_pure_and_database_services_use_the_same_rejection_partition(context):
    from app.services.deduplication_service import DeduplicationService
    from app.services.deduplication_service import PairDecision as Override
    from app.services.record_mapping import to_engine_record
    from tests.fakes import MemoryRepository

    db, review, (a, b, bridge), service = context
    for record in (a, b, bridge):
        record.doi = "10.1000/synthetic-shared"
    db.commit()
    service.score_current_records(review.id)
    verdict(service, review, a, b, "reject")
    pure = DeduplicationService(MemoryRepository()).run(
        [to_engine_record(record) for record in (a, b, bridge)],
        run_id="synthetic-run",
        pair_decisions=[Override(a.id, b.id, "reject")],
    )
    database_groups = {}
    for record in (a, b, bridge):
        database_groups.setdefault(record.group_id, set()).add(record.id)
    assert {frozenset(item) for item in database_groups.values()} == {
        frozenset(item.member_ids) for item in pure.groups
    }
    assert len(pure.conflicts) == 1
