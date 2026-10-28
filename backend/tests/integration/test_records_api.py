"""Integration tests for Records listing, search, pagination, and detail inspection."""

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


def test_records_api_listing_search_and_detail(client):
    # 1. Create a Review
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Heart Failure and SGLT2 Inhibitors",
            "question": "Does empagliflozin reduce cardiovascular death in heart failure?",
            "pico": {"P": "HF patients", "I": "Empagliflozin", "C": "Placebo", "O": "Death"},
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # 2. Formulate Query and Import Records
    q_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — SGLT2 Heart Failure Search",
            "parent_id": None,
            "spec": {"expression": "empagliflozin heart failure", "source": "europe_pmc"},
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
                source_record_id="EMPA_101",
                title="Empagliflozin Outcome Trial in Heart Failure with Preserved Ejection Fraction",
                authors=[Author(full_name="Anker SD"), Author(full_name="Butler J")],
                journal="N Engl J Med",
                year=2021,
                doi="10.1056/NEJMoa2107038",
                pmid="34449189",
                abstract="Empagliflozin reduced the combined risk of cardiovascular death or hospitalization for heart failure.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="EMPA_102_DUP",
                title="Empagliflozin in Heart Failure with Preserved EF (EMPEROR-Preserved)",
                authors=[Author(full_name="Anker SD")],
                journal="NEJM",
                year=2021,
                doi="10.1056/NEJMoa2107038",
                abstract="Cardiovascular death reduced with empagliflozin.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="DAPA_201",
                title="Dapagliflozin in Patients with Heart Failure and Reduced Ejection Fraction",
                authors=[Author(full_name="McMurray JJV")],
                journal="N Engl J Med",
                year=2019,
                doi="10.1056/NEJMoa1911303",
                pmid="31535829",
                abstract="Dapagliflozin was superior to placebo in reducing heart failure progression.",
            ),
        ]
        q_service.import_query(query_id, records_in=records)

        # Ingest exact duplicate pair between EMPA_101 and EMPA_102_DUP
        r1 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "EMPA_101")
            .first()
        )
        r2 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "EMPA_102_DUP")
            .first()
        )
        r3 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "DAPA_201")
            .first()
        )

        assert r1 and r2 and r3
    finally:
        db.close()

    # 3. Test GET /api/reviews/{id}/records (Representatives only)
    res_reps = client.get(f"/api/reviews/{review_id}/records?representatives_only=true")
    assert res_reps.status_code == 200
    data_reps = res_reps.json()
    assert data_reps["total"] == 2  # EMPA canonical + DAPA canonical
    assert len(data_reps["items"]) == 2
    assert all(item["is_representative"] is True for item in data_reps["items"])

    # 4. Test GET /api/reviews/{id}/records (All records including duplicates)
    res_all = client.get(f"/api/reviews/{review_id}/records?representatives_only=false")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 3

    # 5. Test Keyword Search q='Dapagliflozin'
    res_search = client.get(
        f"/api/reviews/{review_id}/records?q=Dapagliflozin&representatives_only=false"
    )
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] == 1
    assert data_search["items"][0]["source_record_id"] == "DAPA_201"

    # 6. Test Pagination
    res_page = client.get(
        f"/api/reviews/{review_id}/records?page=1&page_size=1&representatives_only=false"
    )
    assert res_page.status_code == 200
    data_page = res_page.json()
    assert data_page["total"] == 3
    assert len(data_page["items"]) == 1
    assert data_page["page"] == 1
    assert data_page["page_size"] == 1

    # 7. Test GET /api/records/{id} (Detailed Record View)
    res_detail = client.get(f"/api/records/{r1.id}")
    assert res_detail.status_code == 200
    data_detail = res_detail.json()
    assert data_detail["id"] == r1.id
    assert data_detail["doi"] == "10.1056/NEJMoa2107038"
    assert "reduced the combined risk" in data_detail["abstract"]
    assert len(data_detail["cluster_members"]) == 1
    assert data_detail["cluster_members"][0]["source_record_id"] == "EMPA_102_DUP"

    # 8. Test 404 for non-existent record
    res_404 = client.get("/api/records/00000000-0000-0000-0000-000000000000")
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "NOT_FOUND"
