"""Integration tests for Conflict listing, consensus resolution, and audit trail."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.audit import AuditEvent
from app.models.record import Record
from app.models.screening import ScreeningDecision
from app.schemas.contracts import Author, LiteratureSource, RecordIn
from app.services.query_service import QueryService


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_conflict_pipeline_and_consensus_resolution(client):
    # 1. Setup Review and Record
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Conflict Resolution Pipeline",
            "question": "Is Metformin effective in pre-diabetes prevention?",
            "pico": {
                "P": "Pre-diabetic adults",
                "I": "Metformin",
                "C": "Lifestyle",
                "O": "Incidence",
            },
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    q_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — Metformin Diabetes Prevention",
            "parent_id": None,
            "spec": {"expression": "metformin prediabetes prevention", "source": "europe_pmc"},
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
                source_record_id="MET_101",
                title="Metformin in Prevention of Type 2 Diabetes",
                authors=[Author(full_name="Knowler WC")],
                year=2002,
                doi="10.1056/NEJMoa012512",
                abstract="Metformin reduced diabetes incidence by 31% compared with placebo.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="MET_102_DUP",
                title="Metformin in Prevention of Type 2 Diabetes (Duplicate)",
                authors=[Author(full_name="Knowler WC")],
                year=2002,
                doi="10.1056/NEJMoa012512",
                abstract="Metformin reduced diabetes incidence by 31% compared with placebo.",
            ),
        ]
        q_service.import_query(query_id, records_in=records)

        rec = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "MET_101")
            .first()
        )
        assert rec is not None
        rec_id = rec.id
    finally:
        db.close()

    # 2. Reviewer A screens INCLUDE
    res_a = client.post(
        f"/api/records/{rec_id}/screening",
        json={
            "decision": "include",
            "reviewer_name": "Reviewer A (Cardiologist)",
            "note": "Landmark trial, exact population",
        },
    )
    assert res_a.status_code == 201

    # 3. Reviewer B screens EXCLUDE with reason -> Triggers Conflict
    res_b = client.post(
        f"/api/records/{rec_id}/screening",
        json={
            "decision": "exclude",
            "reviewer_name": "Reviewer B (Methodologist)",
            "reason_text": "Non-blinded intervention arm in trial protocol",
        },
    )
    assert res_b.status_code == 201

    # 4. Query GET /api/reviews/{id}/conflicts (open)
    conf_res = client.get(f"/api/reviews/{review_id}/conflicts?status=open")
    assert conf_res.status_code == 200
    conflicts = conf_res.json()
    assert len(conflicts) == 1
    conflict_id = conflicts[0]["id"]
    assert conflicts[0]["reason"] == "include_vs_exclude"
    assert conflicts[0]["status"] == "open"

    # 5. Non-negotiable invariant: If resolving as exclude, must provide reason
    fail_resolve = client.post(
        f"/api/conflicts/{conflict_id}/resolve",
        json={
            "decision": "exclude",
            "reviewer": "Consensus Committee",
            "criterion_id": None,
            "reason_text": None,
        },
    )
    assert fail_resolve.status_code == 422

    # 6. Resolve conflict as INCLUDE by Consensus Panel
    resolve_res = client.post(
        f"/api/conflicts/{conflict_id}/resolve",
        json={
            "decision": "include",
            "reviewer": "Consensus Panel (Lin & Patel)",
            "note": "Panel agreed open-label design is acceptable given objective glucose outcome.",
        },
    )
    assert resolve_res.status_code == 200
    res_body = resolve_res.json()
    assert res_body["status"] == "resolved"
    assert res_body["conflict_id"] == conflict_id
    assert res_body["affected_records_count"] == 2  # Propagated to both records in the cluster

    # 7. Verify GET /api/reviews/{id}/conflicts (open is empty, resolved has the record)
    open_res = client.get(f"/api/reviews/{review_id}/conflicts?status=open")
    assert open_res.status_code == 200
    assert len(open_res.json()) == 0

    resolved_res = client.get(f"/api/reviews/{review_id}/conflicts?status=resolved")
    assert resolved_res.status_code == 200
    assert len(resolved_res.json()) == 1
    assert resolved_res.json()[0]["status"] == "resolved"
    assert resolved_res.json()[0]["resolved_by"] == "Consensus Panel (Lin & Patel)"

    # 8. Verify DB State: all cluster records have consensus decision with origin='conflict_resolution'
    db = SessionLocal()
    try:
        active_decisions = (
            db.query(ScreeningDecision)
            .filter(
                ScreeningDecision.superseded_by_id.is_(None),
            )
            .join(Record, Record.id == ScreeningDecision.record_id)
            .filter(Record.review_id == review_id)
            .all()
        )
        assert len(active_decisions) == 2
        for dec in active_decisions:
            assert dec.decision == "include"
            assert dec.origin == "conflict_resolution"

        # Check Audit Log
        audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.review_id == review_id, AuditEvent.event_type == "conflict_resolved")
            .first()
        )
        assert audit is not None
        assert audit.actor == "Consensus Panel (Lin & Patel)"
        assert audit.after_state["status"] == "resolved"
    finally:
        db.close()
