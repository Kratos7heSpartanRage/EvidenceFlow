"""Live import pipeline through the real API, with a fake literature source.

Covers: the Import button runs fetch -> store -> dedup -> screen -> PICO;
provenance links for already-stored records (Scenario B); incremental fetch;
idempotent re-posts; source failures that keep the database clean; retry.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.base import SourceError
from app.core.database import SessionLocal
from app.main import app
from app.models.audit import AuditEvent, PipelineRun
from app.models.pico import PICOAnnotation
from app.models.query import QueryRecord, QueryVersion
from app.models.record import Record
from app.models.review import Criterion
from app.models.screening import ScreeningDecision, ScreeningSuggestion
from app.schemas.contracts import Author, RecordIn, SearchResult
from app.services.import_pipeline import criterion_specs, pico_terms, record_content_hash
from app.services.query_service import QueryService

HUMAN_RCT = RecordIn(
    source="europe_pmc",
    source_record_id="MED:1001",
    title="Metformin versus placebo in adults with type 2 diabetes",
    abstract=(
        "Adults with type 2 diabetes received metformin or placebo for 12 weeks. "
        "The primary outcome was change in HbA1c."
    ),
    authors=[Author(full_name="Rao A", last_name="Rao")],
    year=2021,
    doi="10.1000/live-import.1001",
    pmid="1001",
    language="eng",
    pub_types=["Randomized Controlled Trial"],
    mesh_terms=["Humans", "Metformin"],
)
RAT_STUDY = RecordIn(
    source="europe_pmc",
    source_record_id="MED:1002",
    title="Metformin in a rat model of insulin resistance",
    abstract="Male Wistar rats were fed a high-fat diet and treated with metformin.",
    authors=[Author(full_name="Weber D", last_name="Weber")],
    year=2019,
    pmid="1002",
    language="eng",
    pub_types=["Journal Article"],
    mesh_terms=["Animals", "Rats"],
)
NO_ABSTRACT = RecordIn(
    source="europe_pmc",
    source_record_id="PPR:1003",
    title="Long-term metformin outcomes: a protocol",
    year=2022,
)
NEW_IN_V2 = RecordIn(
    source="europe_pmc",
    source_record_id="MED:1004",
    title="Metformin and cardiovascular outcomes in older adults with type 2 diabetes",
    abstract="Older adults with type 2 diabetes received metformin. Mortality was measured.",
    year=2023,
    doi="10.1000/live-import.1004",
)


class FakeSource:
    """Honours known_ids like the real adapters and records every call."""

    def __init__(self, hit_count: int, records: list[RecordIn], fail: SourceError | None = None):
        self.hit_count, self.records, self.fail = hit_count, records, fail
        self.calls: list[dict] = []

    def search(self, spec, cap, known_ids=frozenset()):
        self.calls.append({"spec": spec, "cap": cap, "known_ids": set(known_ids)})
        if self.fail is not None:
            raise self.fail
        ids = [record.source_record_id for record in self.records][:cap]
        fresh = [
            r
            for r in self.records
            if r.source_record_id not in known_ids and r.source_record_id in ids
        ]
        return SearchResult(
            hit_count=self.hit_count,
            ids=ids,
            records=fresh,
            skipped_known=len(ids) - len(fresh),
            truncated=self.hit_count > cap,
            warnings=["fixture warning"],
        )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def use_source(monkeypatch):
    def install(source: FakeSource) -> FakeSource:
        monkeypatch.setattr("app.services.import_pipeline.source_adapter", lambda name: source)
        return source

    return install


def create_review(client) -> str:
    response = client.post(
        "/api/reviews",
        json={
            "title": "Live import pipeline",
            "question": "Does metformin lower HbA1c in adults with type 2 diabetes?",
            "pico": {
                "population": "adults with type 2 diabetes",
                "intervention": "metformin",
                "comparator": "placebo",
                "outcome": "HbA1c",
            },
            "initial_criteria": [
                {
                    "type": "exclusion",
                    "label": "Animal study",
                    "description": "The review is about treatment in people.",
                    "detector_rule": "non_human",
                },
                {
                    "type": "inclusion",
                    "label": "Adults",
                    "description": "Participants aged 18 or over.",
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_frozen_query(client, review_id: str, parent_id: str | None = None) -> str:
    response = client.post(
        f"/api/reviews/{review_id}/queries",
        json={
            "label": "metformin search",
            "parent_id": parent_id,
            "spec": {"source": "europe_pmc", "expression": "metformin AND diabetes"},
        },
    )
    assert response.status_code == 201, response.text
    query_id = response.json()["id"]
    with SessionLocal() as db:
        QueryService(db).preview_query(query_id, sample_records=[], estimated_hits=3)
    return query_id


def post_import(client, query_id: str) -> dict:
    response = client.post(f"/api/queries/{query_id}/import")
    assert response.status_code == 202, response.text
    return response.json()


def record_ids(db, review_id: str) -> dict[str, str]:
    return {
        r.source_record_id: r.id for r in db.query(Record).filter(Record.review_id == review_id)
    }


def test_import_button_runs_the_whole_pipeline(client, use_source):
    source = use_source(FakeSource(13790, [HUMAN_RCT, RAT_STUDY, NO_ABSTRACT]))
    review_id = create_review(client)
    query_id = create_frozen_query(client, review_id)

    started = post_import(client, query_id)
    assert started["status"] == "queued"

    run = client.get(f"/api/runs/{started['run_id']}").json()
    assert run["status"] == "completed", run
    assert run["progress_percent"] == 100
    assert [step["status"] for step in run["steps"]] == ["completed"] * 4
    fetch_message = run["steps"][0]["message"]
    assert "13790 hits" in fetch_message and "3 new" in fetch_message
    assert "fixture warning" in fetch_message
    assert source.calls[0]["known_ids"] == set()
    assert source.calls[0]["spec"].expression == "metformin AND diabetes"

    with SessionLocal() as db:
        ids = record_ids(db, review_id)
        assert set(ids) == {"MED:1001", "MED:1002", "PPR:1003"}
        rct = db.get(Record, ids["MED:1001"])
        assert rct.raw_payload["content_hash"] == record_content_hash(HUMAN_RCT)
        assert len(rct.raw_payload["content_hash"]) == 64

        links = db.query(QueryRecord).filter_by(query_version_id=query_id).count()
        assert links == 3
        query = db.get(QueryVersion, query_id)
        assert (query.status, query.hit_count, query.imported_count) == ("approved", 13790, 3)

        def suggestion(source_record_id):
            rows = db.query(ScreeningSuggestion).filter_by(record_id=ids[source_record_id]).all()
            assert len(rows) == 1
            return rows[0]

        animal = db.query(Criterion).filter_by(label="Animal study").one()
        rat = suggestion("MED:1002")
        assert rat.suggested_decision == "exclude"
        assert rat.matched_criterion_id == animal.id
        assert rat.matched_criterion_label == "Animal study"
        assert {"code": "strength", "strength": "strong"} in rat.evidence_snippets
        assert suggestion("PPR:1003").suggested_decision == "maybe"  # no abstract
        assert suggestion("MED:1001").suggested_decision in {"include", "maybe"}

        # Machine output only: no human decisions were written.
        assert (
            db.query(ScreeningDecision)
            .filter(ScreeningDecision.record_id.in_(ids.values()))
            .count()
            == 0
        )

        def spans(source_record_id):
            return db.query(PICOAnnotation).filter_by(record_id=ids[source_record_id]).all()

        assert spans("MED:1001") and all(span.origin == "machine" for span in spans("MED:1001"))
        assert spans("MED:1002") == []  # suggested exclude: not tagged
        for span in spans("MED:1001"):
            assert rct.abstract[span.start_index : span.end_index] == span.text

        assert (
            db.query(AuditEvent)
            .filter_by(target_id=query_id, event_type="import_pipeline_completed")
            .count()
            == 1
        )


def test_reposting_import_returns_the_same_run_and_adds_nothing(client, use_source):
    source = use_source(FakeSource(3, [HUMAN_RCT, RAT_STUDY, NO_ABSTRACT]))
    review_id = create_review(client)
    query_id = create_frozen_query(client, review_id)
    first = post_import(client, query_id)
    with SessionLocal() as db:
        before = (
            db.query(Record).filter_by(review_id=review_id).count(),
            db.query(ScreeningSuggestion).count(),
            db.query(PICOAnnotation).count(),
        )

    again = post_import(client, query_id)
    assert again == {"run_id": first["run_id"], "status": "completed"}
    assert len(source.calls) == 1
    with SessionLocal() as db:
        after = (
            db.query(Record).filter_by(review_id=review_id).count(),
            db.query(ScreeningSuggestion).count(),
            db.query(PICOAnnotation).count(),
        )
        assert after == before
        assert db.query(PipelineRun).filter_by(query_version_id=query_id).count() == 1


def test_second_version_links_known_records_and_fetches_only_new_ones(client, use_source):
    use_source(FakeSource(3, [HUMAN_RCT, RAT_STUDY, NO_ABSTRACT]))
    review_id = create_review(client)
    v1 = create_frozen_query(client, review_id)
    post_import(client, v1)

    v2_source = use_source(FakeSource(2, [RAT_STUDY, NEW_IN_V2]))
    v2 = create_frozen_query(client, review_id, parent_id=v1)
    run = client.get(f"/api/runs/{post_import(client, v2)['run_id']}").json()
    assert run["status"] == "completed", run

    # The adapter was told what is already stored, so the rat study is not refetched.
    assert v2_source.calls[0]["known_ids"] == {"MED:1001", "MED:1002", "PPR:1003"}
    assert "1 new, 1 already stored; 2 linked" in run["steps"][0]["message"]

    with SessionLocal() as db:
        ids = record_ids(db, review_id)
        assert len(ids) == 4  # one row per paper, never a copy
        v2_links = {link.record_id for link in db.query(QueryRecord).filter_by(query_version_id=v2)}
        # Scenario B: the previously excluded record is linked to v2 as well.
        assert v2_links == {ids["MED:1002"], ids["MED:1004"]}
        v1_links = db.query(QueryRecord).filter_by(query_version_id=v1).count()
        assert v1_links == 3
        # Unchanged records are not re-screened.
        assert db.query(ScreeningSuggestion).filter_by(record_id=ids["MED:1002"]).count() == 1
        assert db.query(ScreeningSuggestion).filter_by(record_id=ids["MED:1004"]).count() == 1


def test_source_failure_keeps_database_clean_and_retry_succeeds(client, use_source):
    use_source(FakeSource(0, [], fail=SourceError("timeout", "europe_pmc", "Fixture timeout")))
    review_id = create_review(client)
    query_id = create_frozen_query(client, review_id)

    failed_id = post_import(client, query_id)["run_id"]
    failed = client.get(f"/api/runs/{failed_id}").json()
    assert failed["status"] == "failed"
    assert "Fixture timeout" in failed["error_message"]
    assert [step["status"] for step in failed["steps"]] == ["failed", "queued", "queued", "queued"]
    with SessionLocal() as db:
        assert db.query(Record).filter_by(review_id=review_id).count() == 0
        assert db.query(QueryRecord).filter_by(query_version_id=query_id).count() == 0

    use_source(FakeSource(1, [HUMAN_RCT]))
    retry = post_import(client, query_id)
    assert retry["run_id"] != failed_id
    assert client.get(f"/api/runs/{retry['run_id']}").json()["status"] == "completed"
    with SessionLocal() as db:
        assert db.query(Record).filter_by(review_id=review_id).count() == 1


def test_unpreviewed_query_cannot_be_imported(client, use_source):
    source = use_source(FakeSource(1, [HUMAN_RCT]))
    review_id = create_review(client)
    response = client.post(
        f"/api/reviews/{review_id}/queries",
        json={"label": "draft", "spec": {"source": "europe_pmc", "expression": "metformin"}},
    )
    query_id = response.json()["id"]

    response = client.post(f"/api/queries/{query_id}/import")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert source.calls == []
    with SessionLocal() as db:
        assert db.query(PipelineRun).filter_by(query_version_id=query_id).count() == 0


# --------------------------------------------------------------- pure helpers


def test_criteria_mapping_uses_detector_rule_never_labels():
    criteria = [
        Criterion(
            id="c1",
            type="exclusion",
            label="Animals",
            description="Humans only",
            detector_rule="NON_HUMAN",
        ),
        Criterion(
            id="c2",
            type="exclusion",
            label="Paediatric",
            description="Adults only",
            detector_rule="children| infants |",
        ),
        Criterion(id="c3", type="inclusion", label="non_human", description="No rule set"),
    ]
    specs = criterion_specs(criteria)
    assert [(s.id, s.code, s.kind, s.detector) for s in specs] == [
        ("c1", "non_human", "exclude", "metadata_then_rule"),
        ("c2", "custom_keyword", "exclude", "rule"),
        ("c3", "manual", "include", "manual_only"),
    ]
    assert list(specs[1].params["terms"]) == ["children", "infants"]
    assert specs[0].reason == "Humans only"


def test_pico_terms_accept_full_or_letter_keys_and_lists():
    full = pico_terms({"population": "adults; older adults", "intervention": "metformin"})
    assert full.population == ("adults", "older adults")
    assert full.intervention == ("metformin",)
    letters = pico_terms({"P": "Patients", "I": "Drug A, Drug B", "C": "", "O": None})
    assert letters.intervention == ("Drug A", "Drug B")
    assert letters.comparator == () and letters.outcome == ()
    assert pico_terms(None) == pico_terms({})
