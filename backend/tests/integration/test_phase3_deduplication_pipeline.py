"""Integration test suite for Phase 3: Deduplication, Grouping, Pair Decisions, and Scenario D Guard."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.audit import AuditEvent
from app.models.dedup import DuplicatePair, GroupSnapshot, PairDecision
from app.models.loop import Conflict
from app.models.record import Record
from app.schemas.contracts import DuplicateTier, LiteratureSource, RecordIn, ScoredPair
from app.services.deduplication_db_service import DatabaseDeduplicationService
from app.services.query_service import QueryService


@pytest.fixture
def client(monkeypatch):
    from app.schemas.contracts import PreviewResult

    class Adapter:
        def preview(self, spec, n=20):
            return PreviewResult(hit_count=4, records=[])

    monkeypatch.setattr("app.services.query_service.source_adapter", lambda source: Adapter())
    with TestClient(app) as test_client:
        yield test_client


def test_deduplication_lifecycle_and_pair_decisions(client):
    # 1. Create a review
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Dual Antiplatelet Therapy in Acute Coronary Syndrome",
            "question": "Is ticagrelor superior to clopidogrel in reducing mortality?",
            "pico": {"P": "ACS patients", "I": "Ticagrelor", "C": "Clopidogrel", "O": "Mortality"},
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # 2. Formulate Query and Import multi-source records (PubMed + Europe PMC)
    q_res = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "v1.0 — Multicenter DAPT Search",
            "parent_id": None,
            "spec": {
                "expression": "ticagrelor AND clopidogrel AND trial",
                "source": "europe_pmc",
            },
        },
    )
    query_id = q_res.json()["id"]

    # Preview query
    client.post(f"/api/queries/{query_id}/preview")

    # Import 4 records
    db = SessionLocal()
    try:
        q_service = QueryService(db)
        records = [
            # rec1: Long abstract, DOI + PMID
            RecordIn(
                source=LiteratureSource.PUBMED,
                source_record_id="PMID_1001",
                title="Ticagrelor versus Clopidogrel in Patients with Acute Coronary Syndromes",
                authors=["Wallentin L", "Becker RC", "Budaj A"],
                journal="N Engl J Med",
                publication_year=2009,
                doi="10.1056/NEJMoa0904327",
                pmid="19717846",
                abstract="In patients who have an acute coronary syndrome with or without ST-segment elevation, treatment with ticagrelor significantly reduced the rate of death from vascular causes, myocardial infarction, or stroke.",
            ),
            # rec2: Duplicate from Europe PMC (same paper, shorter abstract, same DOI)
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="PMC_PLATO",
                title="Ticagrelor versus Clopidogrel in Patients with Acute Coronary Syndromes (PLATO Trial)",
                authors=["Wallentin L", "Becker RC"],
                journal="NEJM",
                publication_year=2009,
                doi="10.1056/NEJMoa0904327",
                abstract="Ticagrelor compared with clopidogrel significantly reduced ischemic events.",
            ),
            # rec3: High confidence candidate duplicate study
            RecordIn(
                source=LiteratureSource.PUBMED,
                source_record_id="PMID_2001",
                title="Platelet Inhibition with Ticagrelor: 12-Month Follow-Up Study",
                authors=["Storey RF", "Angiolillo DJ"],
                journal="J Am Coll Cardiol",
                publication_year=2010,
                doi="10.1016/j.jacc.2010.05.01",
                pmid="20688210",
                abstract="Pharmacodynamic assessment showed consistent platelet inhibition over 12 months.",
            ),
            # rec4: Same study reported with alternate title
            RecordIn(
                source=LiteratureSource.EUROPE_PMC,
                source_record_id="PMC_2002",
                title="Platelet Inhibition with Ticagrelor: A 12-Month Follow-Up Investigation",
                authors=["Storey RF", "Angiolillo DJ"],
                journal="JACC",
                publication_year=2010,
                abstract="Consistent platelet inhibition observed over 12 months in coronary patients.",
            ),
        ]
        # Each query has one source; preserve provenance using separate versions.
        q_service.import_query(
            query_id, records_in=[r for r in records if r.source == LiteratureSource.EUROPE_PMC]
        )
        pubmed_query = client.post(
            f"/api/reviews/{review_id}/queries",
            json={
                "label": "PubMed fixture search",
                "spec": {"source": "pubmed", "expression": "trial"},
            },
        ).json()["id"]
        client.post(f"/api/queries/{pubmed_query}/preview")
        q_service.import_query(
            pubmed_query, records_in=[r for r in records if r.source == LiteratureSource.PUBMED]
        )
    finally:
        db.close()

    # 3. Ingest candidate duplicate pairs
    db = SessionLocal()
    try:
        rec1 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "PMID_1001")
            .first()
        )
        rec2 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "PMC_PLATO")
            .first()
        )
        rec3 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "PMID_2001")
            .first()
        )
        rec4 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "PMC_2002")
            .first()
        )

        assert rec1 and rec2 and rec3 and rec4

        dedup_service = DatabaseDeduplicationService(db)
        scored_pairs = [
            # Tier 2 candidate match
            ScoredPair(
                record_a_id=rec3.id,
                record_b_id=rec4.id,
                similarity_score=0.91,
                tier=DuplicateTier.TIER_2_HIGH_CONFIDENCE,
                match_reasons=["author_overlap_0.95", "title_cosine_0.92"],
            ),
        ]
        dedup_service.ingest_candidate_pairs(review_id, scored_pairs)

        # Execute clustering
        cluster_res = dedup_service.cluster_records(review_id)
        assert cluster_res["total_records"] == 4

        # Verify Canonical Election for Tier 1 Pair (rec1 vs rec2)
        # rec1 has DOI + PMID + longer abstract -> must be canonical representative!
        db.refresh(rec1)
        db.refresh(rec2)
        assert rec1.group_id == rec2.group_id
        assert rec1.is_representative is True
        assert rec2.is_representative is False

        # rec3 and rec4 are Tier 2 (not confirmed yet) -> must be in separate groups
        db.refresh(rec3)
        db.refresh(rec4)
        assert rec3.group_id != rec4.group_id
    finally:
        db.close()

    # 4. Query Duplicate Pairs via REST API
    pairs_res = client.get(f"/api/reviews/{review_id}/duplicate-pairs?decided=false")
    assert pairs_res.status_code == 200
    pairs_list = pairs_res.json()
    assert len(pairs_list) >= 2

    # Verify side-by-side record summaries exist in response
    tier2_pair = next(p for p in pairs_list if p["tier"] == "tier_2_high_confidence")
    assert tier2_pair["record_a"] is not None
    assert tier2_pair["record_b"] is not None
    assert tier2_pair["similarity_score"] == 0.91

    # 5. Human Decision: Confirm Tier 2 Pair as Duplicate
    pair_decision_payload = {
        "duplicate_pair_id": tier2_pair["id"],
        "decision": "confirm",
        "reviewer_name": "Dr. Sarah Cardiologist",
        "note": "Verified identical trial published under variant titles",
    }
    dec_res = client.post(f"/api/reviews/{review_id}/pair-decisions", json=pair_decision_payload)
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["status"] == "recorded"

    # Verify rec3 and rec4 are now in the SAME group
    db = SessionLocal()
    try:
        r3 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "PMID_2001")
            .first()
        )
        r4 = (
            db.query(Record)
            .filter(Record.review_id == review_id, Record.source_record_id == "PMC_2002")
            .first()
        )
        assert r3.group_id == r4.group_id
        # r3 has PMID and DOI, r4 has no DOI/PMID -> r3 is canonical
        assert r3.is_representative is True
        assert r4.is_representative is False
    finally:
        db.close()

    # 6. Verify GroupSnapshot was captured
    db = SessionLocal()
    try:
        snapshots = db.query(GroupSnapshot).filter(GroupSnapshot.query_version_id == query_id).all()
        assert len(snapshots) == 2
        snap_rec1 = next(s for s in snapshots if s.record_id == rec2.id)
        assert snap_rec1.is_representative == "true"
    finally:
        db.close()

    # 7. Audit Verification: Ensure human pair decision logged immutable audit entry
    db = SessionLocal()
    try:
        audit_logs = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.review_id == review_id,
                AuditEvent.event_type == "pair_decision_recorded",
            )
            .all()
        )
        assert len(audit_logs) >= 1
        latest_audit = audit_logs[0]
        assert latest_audit.actor == "Dr. Sarah Cardiologist"
        assert latest_audit.target_type == "duplicate_pair"
        assert latest_audit.target_id == tier2_pair["id"]
        assert latest_audit.after_state["decision"] == "confirm"
        assert "Verified identical trial" in latest_audit.note
    finally:
        db.close()


def test_scenario_d_pair_override_bypass_guard(client):
    """Scenario D: When a human reviewer explicitly rejects a pair (X, Y),

    transitive connections through intermediate records MUST NOT merge them.
    The system must keep them separate and flag a pair_override_bypassed conflict.
    """
    # 1. Create Review
    rev_res = client.post(
        "/api/reviews",
        json={
            "title": "Scenario D Verification Review",
            "question": "Testing transitive override guards.",
            "pico": {"P": "Patients"},
        },
    )
    review_id = rev_res.json()["id"]

    db = SessionLocal()
    try:
        # Create 3 records: X, Y, and bridge Z
        rec_x = Record(
            review_id=review_id,
            source="pubmed",
            source_record_id="REC_X",
            title="Study X on Drug Alpha",
            doi="10.1000/alpha",
        )
        rec_y = Record(
            review_id=review_id,
            source="pubmed",
            source_record_id="REC_Y",
            title="Study Y on Drug Alpha Sub-analysis",
            doi="10.1000/alpha_sub",
        )
        rec_z = Record(
            review_id=review_id,
            source="europe_pmc",
            source_record_id="REC_Z",
            title="Study Z Linking Trial Metadata",
            doi="10.1000/alpha_meta",
        )
        db.add_all([rec_x, rec_y, rec_z])
        db.commit()
        db.refresh(rec_x)
        db.refresh(rec_y)
        db.refresh(rec_z)

        dedup_service = DatabaseDeduplicationService(db)

        # 2. Reviewer explicitly REJECTS duplicate pair between X and Y
        u, v = sorted([rec_x.id, rec_y.id])
        pair_xy = DuplicatePair(
            review_id=review_id,
            record_a_id=u,
            record_b_id=v,
            similarity_score=0.85,
            tier="tier_2_high_confidence",
            status="rejected_different",
        )
        db.add(pair_xy)
        db.commit()

        # Add human rejection decision
        rej_dec = PairDecision(
            duplicate_pair_id=pair_xy.id,
            decision="reject",
            reviewer_name="Dr. Reviewer",
            note="Separate cohorts, do not merge.",
        )
        db.add(rej_dec)
        db.commit()

        # 3. New candidate pairs connect X to Z and Y to Z (transitive bridge X - Z - Y)
        pair_xz = ScoredPair(
            record_a_id=rec_x.id,
            record_b_id=rec_z.id,
            similarity_score=0.99,
            tier=DuplicateTier.TIER_1_EXACT,
            match_reasons=["exact_match_xz"],
        )
        pair_yz = ScoredPair(
            record_a_id=rec_y.id,
            record_b_id=rec_z.id,
            similarity_score=0.99,
            tier=DuplicateTier.TIER_1_EXACT,
            match_reasons=["exact_match_yz"],
        )
        dedup_service.ingest_candidate_pairs(review_id, [pair_xz, pair_yz])

        # 4. Run clustering
        dedup_service.cluster_records(review_id)

        # 5. Assert Scenario D Invariant:
        # X and Y MUST REMAIN IN SEPARATE GROUPS!
        db.refresh(rec_x)
        db.refresh(rec_y)
        assert rec_x.group_id != rec_y.group_id

        # Assert an open conflict with 'pair_override_bypassed' was created!
        conflict = (
            db.query(Conflict)
            .filter(
                Conflict.review_id == review_id,
                Conflict.reason == "pair_override_bypassed",
                Conflict.status == "open",
            )
            .first()
        )
        assert conflict is not None
        assert "pair_override" in conflict.open_fingerprint
        assert "Transitive conflict link:" in conflict.resolution_note
        assert rec_z.id in conflict.resolution_note
    finally:
        db.close()
