import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.database import SessionLocal, engine
from app.core.errors import (
    ConflictError,
    ImmutableError,
    NotFoundError,
    ValidationError,
)
from app.models.loop import Conflict
from app.models.query import QueryRecord, QueryVersion
from app.models.record import Record
from app.models.review import CriteriaVersion, Criterion, Review
from app.models.screening import ScreeningDecision
from app.schemas.contracts import (
    DuplicateTier,
    ExtractedSpan,
    HeuristicSuggestion,
    LiteratureSource,
    PICOElement,
    QuerySpec,
    RecordIn,
    ScoredPair,
    ScreeningDecisionType,
)


def test_config_defaults():
    settings = Settings()
    assert settings.DATABASE_URL.startswith("sqlite")
    assert settings.HTTP_TIMEOUT == 20
    assert settings.IMPORT_CAP == 500
    assert settings.NCBI_TOOL == "evidenceflow"
    assert "@" in settings.NCBI_EMAIL


def test_error_envelopes():
    err = NotFoundError("Review not found", details={"review_id": "rev-123"})
    envelope = err.to_envelope()
    assert envelope == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Review not found",
            "details": {"review_id": "rev-123"},
        }
    }
    assert err.status_code == 404

    val_err = ValidationError("Exclusion requires reason", details={"field": "reason_text"})
    assert val_err.status_code == 422
    assert val_err.code == "VALIDATION_ERROR"

    conf_err = ConflictError("Open conflict exists")
    assert conf_err.status_code == 409
    assert conf_err.code == "CONFLICT"

    imm_err = ImmutableError()
    assert imm_err.status_code == 409
    assert imm_err.code == "IMMUTABLE_RESOURCE"


def test_schema_contracts():
    query = QuerySpec(
        expression="dementia AND memantine",
        source=LiteratureSource.EUROPE_PMC,
        synonyms=True,
    )
    assert query.source == LiteratureSource.EUROPE_PMC
    assert query.language == "eng"

    rec = RecordIn(
        source=LiteratureSource.PUBMED,
        source_record_id="3456789",
        title="Efficacy of Memantine in Mild to Moderate Dementia",
        authors=["Alice Smith", "Bob Jones"],
        publication_year=2023,
        doi="10.1000/182",
    )
    assert rec.source == LiteratureSource.PUBMED
    assert len(rec.authors) == 2

    pair = ScoredPair(
        record_a_id="rec-1",
        record_b_id="rec-2",
        similarity_score=0.98,
        tier=DuplicateTier.TIER_1_EXACT,
        match_reasons=["exact_doi", "title_cosine_0.99"],
    )
    assert pair.tier == DuplicateTier.TIER_1_EXACT

    suggestion = HeuristicSuggestion(
        record_id="rec-1",
        suggested_decision=ScreeningDecisionType.EXCLUDE,
        confidence=0.88,
        matched_criterion_label="Non-human animal study",
        evidence_snippets=["in Sprague-Dawley rats"],
    )
    assert suggestion.suggested_decision == ScreeningDecisionType.EXCLUDE

    span = ExtractedSpan(
        element=PICOElement.P,
        text="patients with Alzheimer's disease",
        start_index=15,
        end_index=48,
        confidence=0.95,
    )
    assert span.element == PICOElement.P


def test_sqlite_pragmas():
    with engine.connect() as conn:
        fk_result = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert fk_result == 1

        journal_result = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert journal_result.lower() == "wal"


def test_models_lifecycle_and_constraints():
    db = SessionLocal()
    try:
        # 1. Create a Review
        review = Review(
            title="Systematic Review of Memantine in Dementia",
            question="What is the efficacy and safety of memantine in mild-to-moderate dementia?",
            pico={"P": "dementia", "I": "memantine", "C": "placebo", "O": "cognitive scores"},
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        assert review.id is not None

        # 2. Add Criteria Version and Criteria
        c_ver = CriteriaVersion(review_id=review.id, version_number=1)
        db.add(c_ver)
        db.commit()
        db.refresh(c_ver)

        criterion_inc = Criterion(
            criteria_version_id=c_ver.id,
            type="inclusion",
            label="Human subjects",
            description="Must involve human clinical trials",
        )
        criterion_exc = Criterion(
            criteria_version_id=c_ver.id,
            type="exclusion",
            label="Animal studies",
            description="Studies on non-human animals must be excluded",
        )
        db.add_all([criterion_inc, criterion_exc])
        db.commit()
        db.refresh(criterion_exc)

        # 3. Add Records
        rec1 = Record(
            review_id=review.id,
            source="europe_pmc",
            source_record_id="PMC12345",
            title="A Trial of Memantine in Humans",
            authors=["Smith, J."],
            publication_year=2022,
            doi="10.1001/jama.2022.01",
        )
        rec2 = Record(
            review_id=review.id,
            source="pubmed",
            source_record_id="35123456",
            title="Memantine in Rat Models of Alzheimer's",
            authors=["Brown, K."],
            publication_year=2021,
            doi="10.1016/neuro.2021.05",
        )
        db.add_all([rec1, rec2])
        db.commit()
        db.refresh(rec1)
        db.refresh(rec2)

        # 4. Verify Record Idempotency Constraint (review_id, source, source_record_id)
        duplicate_rec = Record(
            review_id=review.id,
            source="europe_pmc",
            source_record_id="PMC12345",  # identical key
            title="Duplicate Title",
        )
        db.add(duplicate_rec)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 5. Non-Negotiable #3: CheckConstraint on Screening Decisions (exclusion requires reason)
        # 5a. Exclusion WITHOUT reason or criterion MUST FAIL
        invalid_decision = ScreeningDecision(
            record_id=rec2.id,
            decision="exclude",
            criterion_id=None,
            reason_text=None,
            reviewer_name="Dr. Reviewer",
        )
        db.add(invalid_decision)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 5b. Exclusion WITH criterion_id MUST SUCCEED
        valid_exc_criterion = ScreeningDecision(
            record_id=rec2.id,
            decision="exclude",
            criterion_id=criterion_exc.id,
            reviewer_name="Dr. Reviewer",
        )
        db.add(valid_exc_criterion)
        db.commit()
        assert valid_exc_criterion.id is not None

        # 5c. Exclusion WITH reason_text MUST SUCCEED
        valid_exc_reason = ScreeningDecision(
            record_id=rec2.id,
            decision="exclude",
            reason_text="Wrong study population",
            reviewer_name="Dr. Reviewer 2",
        )
        db.add(valid_exc_reason)
        db.commit()
        assert valid_exc_reason.id is not None

        # 5d. Inclusion WITHOUT reason MUST SUCCEED
        valid_inc = ScreeningDecision(
            record_id=rec1.id,
            decision="include",
            reviewer_name="Dr. Reviewer",
        )
        db.add(valid_inc)
        db.commit()
        assert valid_inc.id is not None

        # 6. Verify Conflict Idempotency via open_fingerprint
        conf1 = Conflict(
            review_id=review.id,
            group_id="grp-1",
            reason="include_vs_exclude",
            status="open",
            open_fingerprint=f"{review.id}:grp-1:include_vs_exclude",
        )
        db.add(conf1)
        db.commit()

        conf2 = Conflict(
            review_id=review.id,
            group_id="grp-1",
            reason="include_vs_exclude",
            status="open",
            open_fingerprint=f"{review.id}:grp-1:include_vs_exclude",
        )
        db.add(conf2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 7. Verify QueryRecord Composite Primary Key
        q_ver = QueryVersion(
            review_id=review.id,
            version_number=1,
            label="Initial Search",
            expression="dementia AND memantine",
            source="europe_pmc",
        )
        db.add(q_ver)
        db.commit()
        db.refresh(q_ver)

        qr1 = QueryRecord(query_version_id=q_ver.id, record_id=rec1.id)
        db.add(qr1)
        db.commit()

        # Test composite primary key duplicate rejection via second session
        db2 = SessionLocal()
        try:
            qr_dup = QueryRecord(query_version_id=q_ver.id, record_id=rec1.id)
            db2.add(qr_dup)
            with pytest.raises(IntegrityError):
                db2.commit()
        finally:
            db2.close()

        # 8. Clean up test review (cascades to all child rows)
        db.delete(review)
        db.commit()

    finally:
        db.close()
