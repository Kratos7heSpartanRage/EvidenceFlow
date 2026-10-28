"""Real database projections for changed criteria and study families."""

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.dedup import DedupGroup
from app.models.record import Record
from app.models.review import CriteriaVersion, Criterion, Review
from app.models.screening import ScreeningDecision
from app.services.innovation_service import changed_criteria, study_families


def test_changed_criterion_flags_only_matching_old_exclusion():
    with SessionLocal() as db:
        review = Review(title="Eligibility changes", question="Who is eligible?")
        db.add(review)
        db.flush()
        old_version = CriteriaVersion(review_id=review.id, version_number=1)
        db.add(old_version)
        db.flush()
        old = Criterion(
            criteria_version_id=old_version.id,
            type="exclusion",
            label="Age",
            description="Adults only",
            detector_rule=None,
        )
        db.add(old)
        db.flush()
        adolescent = Record(
            review_id=review.id,
            source="pubmed",
            source_record_id="age-1",
            title="Treatment trial",
            abstract="Adolescents received the intervention.",
        )
        adult = Record(
            review_id=review.id,
            source="pubmed",
            source_record_id="age-2",
            title="Another trial",
            abstract="Adults received the intervention.",
        )
        db.add_all([adolescent, adult])
        db.flush()
        db.add_all(
            [
                ScreeningDecision(
                    record_id=r.id,
                    decision="exclude",
                    criterion_id=old.id,
                    reviewer_name="Reviewer",
                    reason_text="Adults only",
                )
                for r in (adolescent, adult)
            ]
        )
        new_version = CriteriaVersion(review_id=review.id, version_number=2)
        db.add(new_version)
        db.flush()
        db.add(
            Criterion(
                criteria_version_id=new_version.id,
                type="exclusion",
                label="Age",
                description="Adults and adolescents",
                detector_rule=None,
            )
        )
        db.commit()
        result = changed_criteria(db, review.id)
        assert [item["record_id"] for item in result] == [adolescent.id]
        assert result[0]["matched_new_terms"] == ["adolescents"]
        response = TestClient(app).get(f"/api/reviews/{review.id}/recheck-candidates")
        assert response.status_code == 200
        assert response.json()[0]["record_id"] == adolescent.id


def test_study_families_separate_duplicates_from_trial_reports():
    with SessionLocal() as db:
        review = Review(title="Study families", question="Which reports belong together?")
        db.add(review)
        db.flush()
        group = DedupGroup(review_id=review.id)
        db.add(group)
        db.flush()
        db.add_all(
            [
                Record(
                    review_id=review.id,
                    source="pubmed",
                    source_record_id="one",
                    title="Primary report NCT12345678",
                    group_id=group.id,
                ),
                Record(
                    review_id=review.id,
                    source="europe_pmc",
                    source_record_id="two",
                    title="Primary report NCT12345678",
                    group_id=group.id,
                ),
                Record(
                    review_id=review.id,
                    source="pubmed",
                    source_record_id="three",
                    title="Follow-up report NCT12345678",
                ),
                Record(
                    review_id=review.id,
                    source="pubmed",
                    source_record_id="four",
                    title="Unrelated study",
                ),
            ]
        )
        db.commit()
        result = study_families(db, review.id)
        assert {item["relationship"] for item in result} == {
            "duplicate_records",
            "possible_same_trial",
        }
        assert (
            len(
                next(item for item in result if item["relationship"] == "duplicate_records")[
                    "records"
                ]
            )
            == 2
        )
        response = TestClient(app).get(f"/api/reviews/{review.id}/study-families")
        assert response.status_code == 200
        assert len(response.json()) == 2
