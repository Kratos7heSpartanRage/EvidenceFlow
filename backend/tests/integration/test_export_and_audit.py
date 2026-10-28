"""Integration tests for RFC 4180 CSV Export, conflict quarantine, and Audit Ledger."""

import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.record import Record
from app.schemas.contracts import Author, LiteratureSource, RecordIn
from app.services.query_service import QueryService


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_export_csv_and_audit_ledger_pipeline(client):
    # 1. Setup Review and Query
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "CSV Export & Audit Pipeline",
            "question": "Does Aspirin prevent secondary colorectal adenomas?",
            "pico": {
                "P": "Patients with adenomas",
                "I": "Aspirin",
                "C": "Placebo",
                "O": "Recurrence",
            },
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    q_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — Aspirin Adenoma Prevention",
            "parent_id": None,
            "spec": {"expression": "aspirin colorectal adenoma prevention", "source": "europe_pmc"},
        },
    )
    query_id = q_res.json()["id"]

    db = SessionLocal()
    try:
        q_service = QueryService(db)
        q_service.preview_query(query_id, sample_records=[], estimated_hits=3)
        records = [
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="ASP_001",
                title="Aspirin for the Prevention of Colorectal Adenomas",
                authors=[Author(full_name="Baron JA"), Author(full_name="Cole BF")],
                year=2003,
                doi="10.1056/NEJMoa021735",
                abstract="A daily dose of 81 mg of aspirin was associated with significant reduction in adenoma risk.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="ASP_002",
                title="Low-Dose Aspirin in Colorectal Cancer Prevention",
                authors=[Author(full_name="Sandler RS")],
                year=2003,
                doi="10.1056/NEJMoa021736",
                abstract="Daily aspirin modestly reduced recurrence of colorectal adenomas.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="ASP_003_EXC",
                title="High-Dose Chemotherapy in Murine Colon Carcinoma",
                authors=[Author(full_name="Murine Lab")],
                year=2010,
                abstract="In vitro study of rodent cell line.",
            ),
        ]
        q_service.import_query(query_id, records_in=records)

        r1 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "ASP_001")
            .first()
        )
        r2 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "ASP_002")
            .first()
        )
        r3 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "ASP_003_EXC")
            .first()
        )
        assert r1 and r2 and r3
        r1_id, r2_id, r3_id = r1.id, r2.id, r3.id
    finally:
        db.close()

    # 2. Record Screening Decisions:
    # R1 -> Include
    client.post(
        f"/api/records/{r1_id}/screening",
        json={"decision": "include", "reviewer_name": "Dr. Sarah Lin", "note": "Eligible RCT"},
    )
    # R2 -> Include
    client.post(
        f"/api/records/{r2_id}/screening",
        json={"decision": "include", "reviewer_name": "Dr. Sarah Lin", "note": "Eligible RCT"},
    )
    # R3 -> Exclude with reason
    client.post(
        f"/api/records/{r3_id}/screening",
        json={
            "decision": "exclude",
            "reviewer_name": "Dr. Sarah Lin",
            "reason_text": "Non-human animal study",
        },
    )

    # 3. Export CSV (clean state, no conflicts)
    exp_res = client.get(f"/api/reviews/{review_id}/export.csv")
    assert exp_res.status_code == 200
    assert "text/csv" in exp_res.headers["content-type"]
    assert "X-Conflict-Warning" not in exp_res.headers

    csv_reader = csv.DictReader(io.StringIO(exp_res.text))
    rows = list(csv_reader)
    assert len(rows) == 2
    exported_sources = {row["source_record_id"] for row in rows}
    assert "ASP_001" in exported_sources
    assert "ASP_002" in exported_sources
    assert "ASP_003_EXC" not in exported_sources
    assert all(row["decision"] == "include" for row in rows)
    assert "Baron JA; Cole BF" in rows[0]["authors"] or "Baron JA; Cole BF" in rows[1]["authors"]

    # 4. Trigger Conflict on R2: Reviewer B excludes R2
    client.post(
        f"/api/records/{r2_id}/screening",
        json={
            "decision": "exclude",
            "reviewer_name": "Dr. Alex Patel",
            "reason_text": "Unclear followup duration",
        },
    )

    # 5. Export CSV again: Open conflict triggers quarantine warning header and quarantines R2
    exp_quarantine_res = client.get(f"/api/reviews/{review_id}/export.csv")
    assert exp_quarantine_res.status_code == 200
    assert exp_quarantine_res.headers.get("X-Conflict-Warning") == "QUARANTINE_OPEN_CONFLICTS"

    csv_reader2 = csv.DictReader(io.StringIO(exp_quarantine_res.text))
    rows2 = list(csv_reader2)
    assert len(rows2) == 1
    assert rows2[0]["source_record_id"] == "ASP_001"  # Only R1, R2 is quarantined!

    # 6. Verify Audit Ledger API
    audit_res = client.get(f"/api/reviews/{review_id}/audit?page=1&page_size=20")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total"] >= 4
    assert len(audit_data["items"]) >= 4

    # Filter audit by event_type
    filtered_audit = client.get(f"/api/reviews/{review_id}/audit?event_type=human_screening")
    assert filtered_audit.status_code == 200
    assert all(item["event_type"] == "human_screening" for item in filtered_audit.json()["items"])
