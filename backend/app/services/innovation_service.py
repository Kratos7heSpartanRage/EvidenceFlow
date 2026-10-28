"""Read-only candidate views for changed criteria and linked trial reports."""

import re
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.record import Record
from app.models.review import CriteriaVersion, Review
from app.models.screening import ScreeningDecision

WORDS = re.compile(r"[a-z][a-z0-9-]{3,}")
TRIAL_ID = re.compile(r"\bNCT\d{8}\b", re.IGNORECASE)


def words(text: str | None) -> set[str]:
    return set(WORDS.findall((text or "").lower()))


def excerpt(text: str | None, term: str) -> str:
    value = text or ""
    location = value.lower().find(term.lower()) if term else -1
    start = max(0, location - 70) if location >= 0 else 0
    return value[start : start + 210].strip()


def changed_criteria(db: Session, review_id: str) -> list[dict]:
    if db.get(Review, review_id) is None:
        raise NotFoundError(f"Review '{review_id}' was not found.")
    versions = (
        db.query(CriteriaVersion)
        .filter_by(review_id=review_id)
        .order_by(CriteriaVersion.version_number.desc())
        .limit(2)
        .all()
    )
    if len(versions) < 2:
        return []
    current, previous = versions
    current_by_label = {(c.type, c.label.casefold().strip()): c for c in current.criteria}
    records = {r.id: r for r in db.query(Record).filter_by(review_id=review_id).all()}
    candidates = []
    for old in previous.criteria:
        if old.type != "exclusion":
            continue
        new = current_by_label.get((old.type, old.label.casefold().strip()))
        if new and (new.description, new.detector_rule, new.field_target) == (
            old.description,
            old.detector_rule,
            old.field_target,
        ):
            continue
        added = sorted(words(new.description if new else "") - words(old.description))
        decisions = (
            db.query(ScreeningDecision)
            .filter_by(criterion_id=old.id, decision="exclude", superseded_by_id=None)
            .all()
        )
        for decision in decisions:
            record = records.get(decision.record_id)
            if record is None:
                continue
            evidence = f"{record.title} {record.abstract or ''}"
            matches = [term for term in added if term in words(evidence)]
            if new is not None and not matches:
                continue
            candidates.append(
                {
                    "record_id": record.id,
                    "title": record.title,
                    "original_reason": decision.reason_text or old.label,
                    "old_criterion": old.description,
                    "new_criterion": new.description if new else None,
                    "matched_new_terms": matches,
                    "evidence_excerpt": excerpt(
                        record.abstract or record.title, matches[0] if matches else ""
                    ),
                    "reviewer": decision.reviewer_name,
                    "reason": "criterion_removed" if new is None else "new_terms_in_abstract",
                }
            )
    return sorted(candidates, key=lambda item: (-len(item["matched_new_terms"]), item["title"]))


def study_families(db: Session, review_id: str) -> list[dict]:
    if db.get(Review, review_id) is None:
        raise NotFoundError(f"Review '{review_id}' was not found.")
    records = db.query(Record).filter_by(review_id=review_id).order_by(Record.id).all()
    duplicates: dict[str, list[Record]] = defaultdict(list)
    trials: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        if record.group_id:
            duplicates[record.group_id].append(record)
        for trial_id in set(TRIAL_ID.findall(f"{record.title} {record.abstract or ''}".upper())):
            trials[trial_id].append(record)
    families = []
    for group_id, members in duplicates.items():
        if len(members) > 1:
            families.append(
                {
                    "id": group_id,
                    "relationship": "duplicate_records",
                    "evidence": "Existing deduplication group",
                    "records": [
                        {"id": r.id, "title": r.title, "source": r.source, "pmid": r.pmid}
                        for r in members
                    ],
                }
            )
    for trial_id, members in trials.items():
        distinct_groups = {r.group_id or r.id for r in members}
        if len(distinct_groups) > 1:
            families.append(
                {
                    "id": trial_id,
                    "relationship": "possible_same_trial",
                    "evidence": f"Shared trial registration {trial_id}; human review needed",
                    "records": [
                        {"id": r.id, "title": r.title, "source": r.source, "pmid": r.pmid}
                        for r in members
                    ],
                }
            )
    return sorted(families, key=lambda item: (item["relationship"], item["id"]))
