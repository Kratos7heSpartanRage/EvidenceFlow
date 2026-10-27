"""Regression checks at the A/B/C boundaries, with no live API calls."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.base import SourceError
from app.adapters.europe_pmc import parse_record
from app.core.database import SessionLocal
from app.engines import PicoTerms, extract_pico, score_pairs, screen
from app.engines.dedup import group, group_key, representative
from app.engines.types import CriterionSpec, RecordLite
from app.main import app
from app.models.audit import AuditEvent, PipelineRun
from app.models.query import QueryVersion
from app.models.record import Record
from app.models.review import Review
from app.schemas.contracts import PreviewResult, QuerySpec, RecordIn
from app.schemas.query import QueryCreate
from app.services.query_service import QueryService
from app.services.record_mapping import to_engine_record


@pytest.fixture
def context():
    with SessionLocal() as db:
        review = Review(title="Integration fixture", question="Does the contract compose?", pico={})
        db.add(review)
        db.commit()
        yield db, review, QueryService(db)


def create_query(context, source="europe_pmc", **options):
    _, review, service = context
    return service.create_query(
        review.id,
        QueryCreate(
            label="Integration fixture",
            spec=QuerySpec(source=source, expression="trial", **options),
        ),
    )


def test_legacy_and_adapter_field_names_agree():
    record = RecordIn(
        source="pubmed",
        source_record_id="1",
        title="Fixture",
        publication_year=2020,
        authors=["Smith J"],
        mesh_headings=["Humans"],
        publication_types=["Journal Article"],
        raw_payload={"original": True},
    )
    assert record.year == record.publication_year == 2020
    assert record.mesh_terms == ["Humans"]
    assert record.pub_types == ["Journal Article"]
    assert record.authors[0].full_name == "Smith J"
    assert record.raw == {"original": True}
    assert QuerySpec(source="pubmed", expression="trial", synonyms=True).expand_synonyms


def test_search_options_and_dates_survive_database_roundtrip(context):
    response = create_query(
        context,
        expand_synonyms=True,
        title_abstract_only=True,
        date_from="2020-01-01",
        date_to="2021-01-01",
    )
    db, _, _ = context
    db.expire_all()
    query = db.get(QueryVersion, response.id)
    assert query.title_abstract_only and query.synonyms
    assert query.date_from == "2020-01-01"
    assert response.expand_synonyms and response.title_abstract_only


def test_zero_hit_preview_is_real_cached_and_audited_once(context, monkeypatch):
    calls = []

    class Adapter:
        def preview(self, spec, n):
            calls.append(spec)
            return PreviewResult(hit_count=0, records=[])

    monkeypatch.setattr("app.services.query_service.source_adapter", lambda source: Adapter())
    query = create_query(context, title_abstract_only=True)
    db, _, service = context
    assert service.preview_query(query.id).estimated_hits == 0
    assert service.preview_query(query.id).sample_records == []
    assert len(calls) == 1 and calls[0].title_abstract_only
    assert (
        db.query(AuditEvent).filter_by(target_id=query.id, event_type="query_previewed").count()
        == 1
    )


def test_source_failure_returns_envelope_without_freezing_query(context, monkeypatch):
    class Adapter:
        def preview(self, spec, n):
            raise SourceError("timeout", spec.source.value, "Fixture timeout")

    monkeypatch.setattr("app.services.query_service.source_adapter", lambda source: Adapter())
    query = create_query(context)
    with TestClient(app) as client:
        response = client.post(f"/api/queries/{query.id}/preview")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "SOURCE_ERROR"
    context[0].expire_all()
    assert context[0].get(QueryVersion, query.id).status == "draft"


def test_invalid_date_range_returns_json_422(context):
    with TestClient(app) as client:
        response = client.post(
            f"/api/reviews/{context[1].id}/queries",
            json={
                "label": "Invalid dates",
                "spec": {
                    "source": "pubmed",
                    "expression": "trial",
                    "date_from": "2022-01-01",
                    "date_to": "2020-01-01",
                },
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unwired_background_import_returns_501_without_creating_run(context):
    query = create_query(context)
    with TestClient(app) as client:
        response = client.post(f"/api/queries/{query.id}/import")
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "PIPELINE_NOT_READY"
    assert context[0].query(PipelineRun).filter_by(query_version_id=query.id).count() == 0


def test_invalid_criterion_is_rejected_before_creating_review():
    with SessionLocal() as db:
        count_before = db.query(Review).count()
        with TestClient(app) as client:
            response = client.post(
                "/api/reviews",
                json={
                    "title": "Invalid criterion fixture",
                    "question": "Fixture question",
                    "initial_criteria": [
                        {"type": "unsupported", "label": "Fixture", "description": "Reason"}
                    ],
                },
            )
        assert response.status_code == 422
        assert db.query(Review).count() == count_before


def test_b_adapter_record_persists_and_reaches_c_engines_with_uuid(context):
    fixture = Path(__file__).parents[1] / "fixtures/europe_pmc/search_page1.json"
    record_in = parse_record(
        json.loads(fixture.read_text(encoding="utf-8"))["resultList"]["result"][0]
    )
    query = create_query(context)
    db, review, service = context
    service.preview_query(query.id, sample_records=[], estimated_hits=1)
    result = service.import_query(query.id, records_in=[record_in])
    assert result.status == "awaiting_processing"
    stored = db.query(Record).filter_by(review_id=review.id).one()
    assert stored.source_record_id.startswith("MED:")
    assert stored.raw_payload["normalized"]["pmcid"] == record_in.pmcid
    assert stored.authors[0]["last_name"] == "Rao"
    lite = to_engine_record(stored)
    assert isinstance(lite.id, str) and lite.first_author == "Rao"
    assert "Humans" in lite.mesh and lite.year == record_in.year
    copy = RecordLite(
        "other-internal-uuid",
        title=lite.title,
        pmid=lite.pmid,
        abstract=lite.abstract,
        source="pubmed",
    )
    pairs = score_pairs([lite, copy])
    assert pairs[0].tier == "auto"
    groups = group([lite.id, copy.id], [(pairs[0].record_a_id, pairs[0].record_b_id)])
    assert len(groups) == 1
    assert representative([lite, copy]) in groups[0]
    assert group_key(groups[0])
    terms = PicoTerms(population=("type 2 diabetes",), intervention=("metformin",))
    criterion = CriterionSpec("criterion-uuid", "non_human", reason="Human-only review")
    assert screen(lite, [criterion], terms).decision == "include"
    assert any(span.status == "suggested" for span in extract_pico(lite.abstract, terms))
    run = db.get(PipelineRun, result.run_id)
    assert run.progress_percent == 25 and run.completed_at is None
    assert [step.status for step in run.steps] == ["completed", "queued", "queued", "queued"]
    assert service.import_query(query.id, records_in=[record_in]).run_id == run.id
    assert db.query(Record).filter_by(review_id=review.id).count() == 1
