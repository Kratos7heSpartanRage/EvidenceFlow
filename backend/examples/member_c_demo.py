"""Offline, synthetic demonstration: python -m examples.member_c_demo."""

import json
from dataclasses import asdict

from app.engines import (
    CriterionSpec,
    PicoTerms,
    RecordLite,
    extract_pico,
    group,
    score_pairs,
    screen,
)
from app.engines.dedup import representative


def main() -> None:
    terms = PicoTerms(
        population=("migraine",),
        intervention=("compound x",),
        comparator=("placebo",),
        outcome=("headache days",),
    )
    records = [
        RecordLite(
            1,
            title="Synthetic clinical trial",
            source="pubmed",
            pmid="12345",
            year=2024,
            abstract="Patients with migraine received compound x compared with placebo. "
            "The primary outcome was headache days.",
            language="eng",
            pub_types=("Journal Article",),
            mesh=("Humans",),
        ),
        RecordLite(
            2,
            title="Synthetic clinical trial",
            source="europe_pmc",
            pmid="12345",
            year=2024,
        ),
        RecordLite(
            3,
            title="Synthetic animal experiment",
            source="europe_pmc",
            year=2024,
            abstract="Mice received compound x in an animal model.",
            language="eng",
            mesh=("Animals", "Mice"),
        ),
        RecordLite(4, title="Synthetic record with no abstract"),
    ]
    criteria = [
        CriterionSpec(1, "non_human", reason="This illustrative review evaluates human treatment."),
    ]
    pairs = score_pairs(records)
    groups = group(
        (record.id for record in records),
        ((pair.record_a_id, pair.record_b_id) for pair in pairs if pair.tier == "auto"),
    )
    output = {
        "synthetic_demo": True,
        "duplicate_pairs": [asdict(pair) for pair in pairs],
        "groups": [],
    }
    by_id = {record.id: record for record in records}
    for members in groups:
        record_id = representative(by_id[member] for member in members)
        record = by_id[record_id]
        suggestion = screen(record, criteria, terms)
        output["groups"].append(
            {
                "member_ids": sorted(members),
                "representative_id": record_id,
                "machine_suggestion": asdict(suggestion),
                "pico": [asdict(span) for span in extract_pico(record.abstract, terms)]
                if suggestion.decision in {"include", "maybe"}
                else [],
            }
        )
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
