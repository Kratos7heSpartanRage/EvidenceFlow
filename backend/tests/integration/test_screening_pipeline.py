"""Integration tests for Screening Decisions, cluster propagation, exclusion reason validation, and conflict detection."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.audit import AuditEvent
from app.models.loop import Conflict
from app.models.record import Record
from app.models.screening import ScreeningDecision
from app.schemas.contracts import Author, LiteratureSource, RecordIn
from app.services.query_service import QueryService


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_screening_decisions_propagation_validation_and_conflicts(client):
    # 1. Setup Review and Query with 2 duplicate cluster records
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Screening Pipeline Verification",
            "question": "Does Drug A improve clinical survival?",
            "pico": {"P": "Patients", "I": "Drug A", "C": "Control", "O": "Survival"},
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    q_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — Drug A Screening",
            "parent_id": None,
            "spec": {"expression": "drug A survival", "source": "europe_pmc"},
        },
    )
    query_id = q_res.json()["id"]

    db = SessionLocal()
    try:
        q_service = QueryService(db)
        q_service.preview_query(query_id, sample_records=[], estimated_hits=2)
        records = [
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="REC_A1",
                title="Drug A Phase 3 Survival Analysis",
                authors=[Author(full_name="Scientist Alpha")],
                year=2022,
                doi="10.1000/drug-a-phase3",
                abstract="Survival improved significantly in experimental group.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="REC_A2_DUP",
                title="Drug A Phase 3 Survival Analysis (Duplicate entry)",
                authors=[Author(full_name="Scientist Alpha")],
                year=2022,
                doi="10.1000/drug-a-phase3",
                abstract="Survival improved significantly in experimental group.",
            ),
        ]
        q_service.import_query(query_id, records_in=records)

        rec1 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "REC_A1")
            .first()
        )
        rec2 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "REC_A2_DUP")
            .first()
        )
        assert rec1 and rec2
        assert rec1.group_id == rec2.group_id
        rec1_id, rec2_id, group_id = rec1.id, rec2.id, rec1.group_id
    finally:
        db.close()

    # 2. Strict Invariant: Exclude without reason MUST FAIL with 422
    fail_res = client.post(
        f"/api/records/{rec1_id}/screening",
        json={
            "decision": "exclude",
            "reviewer_name": "Reviewer 1",
            "criterion_id": None,
            "reason_text": None,
        },
    )
    assert fail_res.status_code == 422
    assert "exclusion decision strictly requires" in str(fail_res.json())

    # 3. Successful Include decision with cluster propagation
    inc_res = client.post(
        f"/api/records/{rec1_id}/screening",
        json={
            "decision": "include",
            "reviewer_name": "Dr. Sarah Lin",
            "note": "Meets all primary inclusion criteria",
        },
    )
    assert inc_res.status_code == 201
    dec_data = inc_res.json()
    assert dec_data["record_id"] == rec1_id
    assert dec_data["decision"] == "include"
    assert dec_data["origin"] == "human"

    # Verify database state: both rec1 (human) and rec2 (inherited) received the decision
    db = SessionLocal()
    try:
        d1 = (
            db.query(ScreeningDecision)
            .filter(
                ScreeningDecision.record_id == rec1_id, ScreeningDecision.superseded_by_id.is_(None)
            )
            .first()
        )
        d2 = (
            db.query(ScreeningDecision)
            .filter(
                ScreeningDecision.record_id == rec2_id, ScreeningDecision.superseded_by_id.is_(None)
            )
            .first()
        )
        assert d1 is not None
        assert d1.decision == "include"
        assert d1.origin == "human"

        assert d2 is not None
        assert d2.decision == "include"
        assert d2.origin == "inherited"

        # Check Audit Trail
        audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.review_id == review_id, AuditEvent.target_id == rec1_id)
            .first()
        )
        assert audit is not None
        assert audit.actor == "Dr. Sarah Lin"
        assert audit.event_type == "human_screening"
        assert audit.after_state["decision"] == "include"
    finally:
        db.close()

    # 4. Superseding decision: Same reviewer changes mind to exclude WITH reason
    exc_res = client.post(
        f"/api/records/{rec1_id}/screening",
        json={
            "decision": "exclude",
            "reviewer_name": "Dr. Sarah Lin",
            "reason_text": "Sample size underpowered (n=12)",
        },
    )
    assert exc_res.status_code == 201
    new_dec = exc_res.json()
    assert new_dec["decision"] == "exclude"

    # Check append-only superseding in DB
    db = SessionLocal()
    try:
        old_d1 = db.query(ScreeningDecision).filter(ScreeningDecision.id == d1.id).first()
        assert old_d1.superseded_by_id == new_dec["id"]
    finally:
        db.close()

    # 5. Opposing decision by a DIFFERENT reviewer -> Triggers open Conflict
    conflict_res = client.post(
        f"/api/records/{rec1_id}/screening",
        json={
            "decision": "include",
            "reviewer_name": "Dr. Alex Patel",
            "note": "Power calculation is acceptable per protocol amendment",
        },
    )
    assert conflict_res.status_code == 201

    db = SessionLocal()
    try:
        conflicts = (
            db.query(Conflict)
            .filter(Conflict.review_id == review_id, Conflict.group_id == group_id)
            .all()
        )
        assert len(conflicts) == 1
        assert conflicts[0].status == "open"
        assert conflicts[0].reason == "include_vs_exclude"
        assert "Sarah Lin" in conflicts[0].resolution_note
        assert "Alex Patel" in conflicts[0].resolution_note
    finally:
        db.close()
