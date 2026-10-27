"""Integration tests for PICO curation API (confirm, correct, reject) and audit trails."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.audit import AuditEvent
from app.models.pico import PICOAnnotation
from app.models.record import Record
from app.schemas.contracts import Author, LiteratureSource, RecordIn
from app.services.query_service import QueryService


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_pico_curation_pipeline(client):
    # 1. Setup Review and Record
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "PICO Extraction & Curation",
            "question": "Does SGLT2 inhibitor dapagliflozin improve eGFR?",
            "pico": {"P": "CKD patients", "I": "Dapagliflozin", "C": "Placebo", "O": "eGFR slope"},
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    q_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — PICO Study",
            "parent_id": None,
            "spec": {"expression": "dapagliflozin ckd", "source": "europe_pmc"},
        },
    )
    query_id = q_res.json()["id"]

    db = SessionLocal()
    try:
        q_service = QueryService(db)
        q_service.preview_query(query_id, sample_records=[], estimated_hits=1)
        records = [
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="PICO_STUDY_1",
                title="Dapagliflozin in Patients with Chronic Kidney Disease",
                authors=[Author(full_name="Heerspink HJL")],
                year=2020,
                doi="10.1056/NEJMoa2024816",
                abstract="Patients with CKD were treated with dapagliflozin 10mg once daily.",
            )
        ]
        q_service.import_query(query_id, records_in=records)

        rec = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "PICO_STUDY_1")
            .first()
        )
        assert rec is not None
        rec_id = rec.id

        # Seed 3 initial machine-extracted PICO annotations
        span_p = PICOAnnotation(
            record_id=rec_id,
            element="P",
            text="Patients with CKD",
            start_index=0,
            end_index=17,
            confidence=0.92,
            origin="machine",
            is_confirmed=False,
        )
        span_i = PICOAnnotation(
            record_id=rec_id,
            element="I",
            text="dapagliflozin",
            start_index=35,
            end_index=48,
            confidence=0.88,
            origin="machine",
            is_confirmed=False,
        )
        span_noise = PICOAnnotation(
            record_id=rec_id,
            element="O",
            text="daily",
            start_index=54,
            end_index=59,
            confidence=0.45,
            origin="machine",
            is_confirmed=False,
        )
        db.add_all([span_p, span_i, span_noise])
        db.commit()
        db.refresh(span_p)
        db.refresh(span_i)
        db.refresh(span_noise)
        p_id, i_id, noise_id = span_p.id, span_i.id, span_noise.id
    finally:
        db.close()

    # 2. Apply batch PICO curation: confirm P, correct I to "dapagliflozin 10mg", reject noise
    patch_res = client.patch(
        f"/api/records/{rec_id}/pico",
        json={
            "ops": [
                {"op": "confirm", "span_id": p_id},
                {"op": "correct", "span_id": i_id, "text": "dapagliflozin 10mg"},
                {"op": "reject", "span_id": noise_id},
            ]
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "updated"
    assert patch_res.json()["updated_count"] == 3

    # 3. Verify Database State
    db = SessionLocal()
    try:
        p_span = db.query(PICOAnnotation).filter(PICOAnnotation.id == p_id).first()
        assert p_span.is_confirmed is True
        assert p_span.origin == "human"

        old_i = db.query(PICOAnnotation).filter(PICOAnnotation.id == i_id).first()
        assert old_i.is_confirmed is False

        # Corrected human span created
        corrected_i = (
            db.query(PICOAnnotation)
            .filter(
                PICOAnnotation.record_id == rec_id,
                PICOAnnotation.element == "I",
                PICOAnnotation.origin == "human",
            )
            .first()
        )
        assert corrected_i is not None
        assert corrected_i.text == "dapagliflozin 10mg"
        assert corrected_i.is_confirmed is True

        rejected_span = db.query(PICOAnnotation).filter(PICOAnnotation.id == noise_id).first()
        assert rejected_span.is_confirmed is False

        # Check Audit Log
        audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.review_id == review_id, AuditEvent.event_type == "pico_annotated")
            .first()
        )
        assert audit is not None
        assert audit.target_id == rec_id
        assert audit.after_state["applied_count"] == 3
    finally:
        db.close()

    # 4. Verify Record Detail endpoint returns the updated spans
    detail_res = client.get(f"/api/records/{rec_id}")
    assert detail_res.status_code == 200
    spans = detail_res.json()["pico_spans"]
    assert any(s["text"] == "dapagliflozin 10mg" and s["origin"] == "human" for s in spans)
    assert any(s["text"] == "Patients with CKD" and s["is_confirmed"] is True for s in spans)
