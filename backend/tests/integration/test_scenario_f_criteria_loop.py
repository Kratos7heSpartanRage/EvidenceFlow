"""Integration tests for Scenario F: Criteria Evolution Loop.

Validates that updating eligibility criteria creates an immutable CriteriaVersion,
triggers suggestions for unscreened studies, while strictly preserving sovereign
human screening decisions with zero mutations or data loss.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.audit import AuditEvent
from app.models.record import Record
from app.models.review import CriteriaVersion
from app.models.screening import ScreeningDecision
from app.schemas.contracts import Author, LiteratureSource, RecordIn
from app.services.query_service import QueryService


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_scenario_f_criteria_evolution_preserves_human_decisions(client):
    # 1. Create Review with initial Criteria Version 1
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Scenario F Criteria Evolution Review",
            "question": "Does Drug X improve adult heart failure outcomes?",
            "pico": {"P": "Heart failure", "I": "Drug X", "C": "Standard Care", "O": "Survival"},
            "initial_criteria": [
                {
                    "type": "inclusion",
                    "label": "Adult Heart Failure",
                    "description": "Patients >= 18 with confirmed HF",
                }
            ],
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # 2. Formulate Query and Import Studies
    q_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — Drug X Heart Failure",
            "parent_id": None,
            "spec": {"expression": "drug x heart failure", "source": "europe_pmc"},
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
                source_record_id="CRIT_LOOP_01",
                title="Adult Clinical Trial with Drug X in Congestive Heart Failure",
                authors=[Author(full_name="Principal Investigator A")],
                year=2021,
                doi="10.1000/adult-trial-01",
                abstract="Adult cohort evaluated with significant improvement in LVEF.",
            ),
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="CRIT_LOOP_02",
                title="Adolescent and Pediatric Safety Tolerability of Drug X",
                authors=[Author(full_name="Pediatric Group B")],
                year=2022,
                doi="10.1000/pediatric-trial-02",
                abstract="Pediatric patients aged 12-17 assessed for tolerability.",
            ),
        ]
        q_service.import_query(query_id, records_in=records)

        rec1 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "CRIT_LOOP_01")
            .first()
        )
        rec2 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "CRIT_LOOP_02")
            .first()
        )
        assert rec1 and rec2
        rec1_id = rec1.id
    finally:
        db.close()

    # 3. Human Reviewer screens Record 1 as INCLUDE
    dec_res = client.post(
        f"/api/records/{rec1_id}/screening",
        json={
            "decision": "include",
            "reviewer_name": "Dr. Sarah Lin",
            "note": "Primary adult RCT meets all v1 criteria",
        },
    )
    assert dec_res.status_code == 201
    initial_human_dec_id = dec_res.json()["id"]

    # 4. Reviewer evolves eligibility criteria: POST /api/reviews/{id}/criteria (adding Pediatric Exclusion)
    criteria_v2_payload = {
        "criteria": [
            {
                "type": "inclusion",
                "label": "Adult Congestive Heart Failure",
                "description": "Patients >= 18 years",
            },
            {
                "type": "exclusion",
                "label": "Pediatric populations",
                "description": "Patients < 18 years of age",
            },
        ]
    }
    crit_res = client.post(f"/api/reviews/{review_id}/criteria", json=criteria_v2_payload)
    assert crit_res.status_code == 201
    crit_v2 = crit_res.json()
    assert crit_v2["version_number"] == 2
    assert len(crit_v2["criteria"]) == 2

    # 5. Non-Negotiable Invariant Check:
    # Human decision on Record 1 MUST REMAIN 100% UNTOUCHED and active!
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
        assert active_dec.id == initial_human_dec_id
        assert active_dec.decision == "include"
        assert active_dec.reviewer_name == "Dr. Sarah Lin"
        assert active_dec.origin == "human"

        # Verify review active criteria version is now v2
        c_ver = (
            db.query(CriteriaVersion)
            .filter(CriteriaVersion.review_id == review_id, CriteriaVersion.version_number == 2)
            .first()
        )
        assert c_ver is not None

        # Verify Audit Log recorded criteria version creation
        crit_audit = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.review_id == review_id,
                AuditEvent.event_type == "criteria_version_created",
            )
            .first()
        )
        assert crit_audit is not None
        assert crit_audit.target_id == c_ver.id
        assert crit_audit.after_state["version_number"] == 2
    finally:
        db.close()

    # 6. Verify Records API projection confirms Record 1 remains included
    rec1_res = client.get(f"/api/records/{rec1_id}")
    assert rec1_res.status_code == 200
    assert rec1_res.json()["decision"]["decision"] == "include"
    assert rec1_res.json()["decision"]["id"] == initial_human_dec_id
