"""Integration tests for Scenario E: Exact, Zero-API Revert to historical snapshot."""

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


def test_scenario_e_exact_zero_api_revert(client):
    # 1. Create Review
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Scenario E Revert Verification",
            "question": "Does GLP-1 RA semaglutide reduce obesity?",
            "pico": {"P": "Obese adults", "I": "Semaglutide", "C": "Placebo", "O": "Weight loss"},
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # 2. Formulate Query V1 (Targeted search)
    q1_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — Targeted Semaglutide Trial",
            "parent_id": None,
            "spec": {"expression": "semaglutide obesity trial", "source": "europe_pmc"},
        },
    )
    v1_id = q1_res.json()["id"]

    db = SessionLocal()
    try:
        q_service = QueryService(db)
        q_service.preview_query(v1_id, sample_records=[], estimated_hits=2)
        v1_records = [
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="SEMA_V1_01",
                title="Once-Weekly Semaglutide in Adults with Overweight or Obesity",
                authors=[Author(full_name="Wilding JPH")],
                year=2021,
                doi="10.1056/NEJMoa2032183",
                abstract="Semaglutide resulted in significant reduction in body weight.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="SEMA_V1_02",
                title="Two-year effects of semaglutide in adults with overweight or obesity",
                authors=[Author(full_name="Garvey WT")],
                year=2022,
                doi="10.1038/s41591-022-02026-4",
                abstract="Substantial, sustained weight loss was achieved over 104 weeks.",
            ),
        ]
        q_service.import_query(v1_id, records_in=v1_records)

        rec1 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "SEMA_V1_01")
            .first()
        )
        assert rec1 is not None
        rec1_id = rec1.id
    finally:
        db.close()

    # 3. Human reviewer records screening decision INCLUDE on SEMA_V1_01
    dec_res = client.post(
        f"/api/records/{rec1_id}/screening",
        json={
            "decision": "include",
            "reviewer_name": "Dr. Sarah Lin",
            "note": "Primary landmark trial",
        },
    )
    assert dec_res.status_code == 201

    # 4. Formulate Query V2 (Overly broad search that pulls in 1 noisy unrelated study)
    q2_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v2.0 — Overly Broad Search",
            "parent_id": v1_id,
            "spec": {"expression": "weight loss drugs general", "source": "europe_pmc"},
        },
    )
    v2_id = q2_res.json()["id"]

    db = SessionLocal()
    try:
        q_service = QueryService(db)
        q_service.preview_query(v2_id, sample_records=[], estimated_hits=3)
        v2_records = [
            # 2 retained from V1
            v1_records[0],
            v1_records[1],
            # 1 noisy new record
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="NOISY_V2_03",
                title="Unrelated rodent diet formulation in murine models",
                authors=[Author(full_name="Rodent Lab")],
                year=2020,
                abstract="Rodents fed high-fat chow.",
            ),
        ]
        q_service.import_query(v2_id, records_in=v2_records)
    finally:
        db.close()

    # Verify that in V2 state, total visible records = 3
    res_v2_active = client.get(f"/api/reviews/{review_id}/records?representatives_only=false")
    assert res_v2_active.status_code == 200
    assert res_v2_active.json()["total"] == 3

    # 5. Reviewer executes Scenario E: Revert to V1
    revert_res = client.post(f"/api/queries/{v1_id}/revert")
    assert revert_res.status_code == 200
    rev_data = revert_res.json()
    assert rev_data["status"] == "reverted"
    assert rev_data["restored_version_id"] == v1_id
    assert rev_data["restored_records_count"] == 2
    assert rev_data["hidden_records_count"] == 1

    # 6. Verify Workspace State post-revert
    # Active visible records must now be exactly 2
    res_reverted_active = client.get(f"/api/reviews/{review_id}/records?representatives_only=false")
    assert res_reverted_active.status_code == 200
    assert res_reverted_active.json()["total"] == 2
    active_ids = {r["source_record_id"] for r in res_reverted_active.json()["items"]}
    assert "SEMA_V1_01" in active_ids
    assert "SEMA_V1_02" in active_ids
    assert "NOISY_V2_03" not in active_ids

    # Query hidden records to verify soft-hide
    res_hidden = client.get(
        f"/api/reviews/{review_id}/records?status=hidden&representatives_only=false"
    )
    assert res_hidden.status_code == 200
    assert res_hidden.json()["total"] == 1
    assert res_hidden.json()["items"][0]["source_record_id"] == "NOISY_V2_03"

    # 7. Non-negotiable invariant: V1 Screening Decision remains 100% intact!
    db = SessionLocal()
    try:
        active_dec = (
            db.query(ScreeningDecision)
            .filter(
                ScreeningDecision.record_id == rec1_id,
                ScreeningDecision.superseded_by_id.is_(None),
            )
            .first()
        )
        assert active_dec is not None
        assert active_dec.decision == "include"
        assert active_dec.reviewer_name == "Dr. Sarah Lin"

        # Check Audit Trail
        revert_audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.review_id == review_id, AuditEvent.event_type == "query_reverted")
            .first()
        )
        assert revert_audit is not None
        assert revert_audit.target_id == v1_id
    finally:
        db.close()
