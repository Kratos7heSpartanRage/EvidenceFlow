"""Integration test suite for Phase 2: Review, Query Pipeline, and Loop Architecture."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.schemas.contracts import LiteratureSource, RecordIn
from app.services.query_service import QueryService


@pytest.fixture
def client(monkeypatch):
    from app.schemas.contracts import PreviewResult

    class FixtureAdapter:
        def preview(self, spec, n=20):
            return PreviewResult(
                hit_count=2,
                records=[
                    RecordIn(
                        source=spec.source,
                        source_record_id="fixture-preview",
                        title="Synthetic preview supplied by the test adapter",
                    )
                ],
            )

    monkeypatch.setattr(
        "app.services.query_service.source_adapter", lambda source: FixtureAdapter()
    )
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"
    assert "time" in data


def test_error_envelope_formatting(client):
    # 404 NotFound
    response = client.get("/api/reviews/non-existent-uuid")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()

    # 422 ValidationError (missing required 'question' field)
    invalid_payload = {"title": "Missing Question Review"}
    response = client.post("/api/reviews", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_review_lifecycle_and_criteria_evolution(client):
    # 1. Create a Review with initial criteria
    payload = {
        "title": "SGLT2 Inhibitors in Diabetic Kidney Disease",
        "question": "Do SGLT2 inhibitors reduce renal progression in adults with T2D?",
        "pico": {
            "population": "Adults with T2D and CKD",
            "intervention": "SGLT2 inhibitors",
            "comparator": "Placebo",
            "outcome": "ESRD and renal mortality",
        },
        "initial_criteria": [
            {
                "type": "inclusion",
                "label": "Human adults",
                "description": "Patients >= 18 years old",
                "field_target": "abstract",
            },
            {
                "type": "exclusion",
                "label": "Animal model",
                "description": "Studies on rats, mice or other animals",
                "field_target": "title",
                "detector_rule": "rats|mice|murine",
            },
        ],
    }
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 201
    review = response.json()
    assert review["id"] is not None
    assert review["title"] == payload["title"]
    assert review["active_criteria_version"]["version_number"] == 1
    assert len(review["active_criteria_version"]["criteria"]) == 2
    assert review["counts"]["total_records"] == 0

    review_id = review["id"]

    # 2. Update Review details (PATCH)
    patch_payload = {
        "question": "Updated systematic question on SGLT2 inhibitors and renal outcomes.",
    }
    patch_res = client.patch(f"/api/reviews/{review_id}", json=patch_payload)
    assert patch_res.status_code == 200
    assert patch_res.json()["question"] == patch_payload["question"]

    # 3. Create a new Criteria Version (v2.0)
    criteria_v2_payload = {
        "criteria": [
            {
                "type": "inclusion",
                "label": "Human adults >= 18",
                "description": "Clinical trials only",
            },
            {
                "type": "exclusion",
                "label": "Animal studies",
                "description": "Non-human studies",
            },
            {
                "type": "exclusion",
                "label": "Pediatric cohorts",
                "description": "Age < 18",
            },
        ]
    }
    crit_res = client.post(f"/api/reviews/{review_id}/criteria", json=criteria_v2_payload)
    assert crit_res.status_code == 201
    v2_data = crit_res.json()
    assert v2_data["version_number"] == 2
    assert len(v2_data["criteria"]) == 3

    # 4. Verify review reflects active criteria v2
    get_res = client.get(f"/api/reviews/{review_id}")
    assert get_res.status_code == 200
    assert get_res.json()["active_criteria_version"]["version_number"] == 2


def test_query_versioning_preview_import_and_diff(client):
    # 1. Create base review
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Memantine Review",
            "question": "What is the clinical efficacy of memantine?",
            "pico": {"P": "Alzheimer", "I": "Memantine"},
        },
    )
    review_id = rev_res.json()["id"]

    # 2. Formulate Query Version 1
    q1_payload = {
        "label": "v1.0 — Initial broad search",
        "parent_id": None,
        "spec": {
            "expression": "memantine AND alzheimer",
            "source": "europe_pmc",
            "synonyms": True,
            "date_from": "2020-01-01",
            "date_to": "2024-01-01",
            "language": "eng",
        },
    }
    q1_res = client.post(f"/api/reviews/{review_id}/queries", json=q1_payload)
    assert q1_res.status_code == 201
    q1_data = q1_res.json()
    assert q1_data["version_number"] == 1
    assert q1_data["status"] == "draft"
    q1_id = q1_data["id"]

    # 3. Preview Query Version 1 -> Freezes Query
    prev_res = client.post(f"/api/queries/{q1_id}/preview")
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["is_frozen"] is True
    assert prev_data["estimated_hits"] > 0
    assert len(prev_data["sample_records"]) > 0

    # Verify query status became 'previewed' and frozen_at is set
    q1_check = client.get(f"/api/queries/{q1_id}").json()
    assert q1_check["status"] == "previewed"
    assert q1_check["frozen_at"] is not None

    # 4. Import Query 1 using direct simulated records
    db = SessionLocal()
    try:
        service = QueryService(db)
        # Import 2 records into Query 1
        records_q1 = [
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="PMC1001",
                title="Memantine efficacy in mild Alzheimer's",
                publication_year=2021,
                doi="10.1016/j.neu.2021.01",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="PMC1002",
                title="Cognitive assessment under memantine",
                publication_year=2022,
                doi="10.1016/j.neu.2022.02",
            ),
        ]
        import_res = service.import_query(q1_id, records_in=records_q1)
        assert import_res.status == "awaiting_processing"
    finally:
        db.close()

    # Verify Review counts updated
    rev_after_q1 = client.get(f"/api/reviews/{review_id}").json()
    assert rev_after_q1["counts"]["total_records"] == 2

    # 5. Formulate Query Version 2 evolving from Query 1 (Narrowed search)
    q2_payload = {
        "label": "v2.0 — Narrowed search with clinical trial filter",
        "parent_id": q1_id,
        "spec": {
            "expression": "memantine AND alzheimer AND trial",
            "source": "europe_pmc",
            "synonyms": True,
            "date_from": "2020-01-01",
            "date_to": "2024-01-01",
            "language": "eng",
        },
    }
    q2_res = client.post(f"/api/reviews/{review_id}/queries", json=q2_payload)
    assert q2_res.status_code == 201
    q2_data = q2_res.json()
    assert q2_data["version_number"] == 2
    assert q2_data["parent_id"] == q1_id
    q2_id = q2_data["id"]

    # Preview Query 2
    client.post(f"/api/queries/{q2_id}/preview")

    # Import Query 2 with 1 retained record (PMC1001) and 1 new record (PMC1003)
    db = SessionLocal()
    try:
        service = QueryService(db)
        records_q2 = [
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="PMC1001",  # Overlap / retained from v1
                title="Memantine efficacy in mild Alzheimer's",
                publication_year=2021,
                doi="10.1016/j.neu.2021.01",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="PMC1003",  # Newly introduced in v2
                title="Randomized trial of memantine in moderate AD",
                publication_year=2023,
                doi="10.1016/j.neu.2023.03",
            ),
        ]
        service.import_query(q2_id, records_in=records_q2)
    finally:
        db.close()

    # 6. Test Mathematical Diff between V2 and V1
    diff_res = client.get(f"/api/queries/{q2_id}/diff?against={q1_id}")
    assert diff_res.status_code == 200
    diff = diff_res.json()
    # V1 has {PMC1001, PMC1002}, V2 has {PMC1001, PMC1003}
    # New records in V2: 1 (PMC1003)
    # Retained overlap: 1 (PMC1001)
    # Dropped records from V1: 1 (PMC1002)
    assert diff["new_records_count"] == 1
    assert diff["retained_records_count"] == 1
    assert diff["dropped_records_count"] == 1
    assert diff["query_v1_id"] == q1_id
    assert diff["query_v2_id"] == q2_id
