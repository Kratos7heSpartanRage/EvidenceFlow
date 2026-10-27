"""Service-to-service checks with a test adapter, not SQL/API integration."""

import unittest

from app.engines.types import CriterionSpec, PicoTerms, RecordLite
from app.services.deduplication_service import DeduplicationService, PairDecision
from app.services.pico_service import PicoService
from app.services.screening_service import HumanDecision, ScreeningService
from tests.fakes import MemoryRepository


class MemberCPipelineTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.dedup = DeduplicationService(self.repo)
        self.screening = ScreeningService(self.repo)
        self.pico = PicoService(self.repo)
        self.terms = PicoTerms(population=("migraine",), intervention=("compound x",))
        self.criteria = [CriterionSpec(1, "non_human", reason="Review of human treatment")]
        self.records = [
            RecordLite(
                1,
                title="Clinical trial",
                abstract="Patients with migraine received compound x compared with placebo.",
                source="pubmed",
                pmid="12345",
                mesh=("Humans",),
            ),
            RecordLite(2, title="Clinical trial", source="europe_pmc", pmid="12345"),
            RecordLite(
                3, title="Animal study", abstract="Mice received compound x.", mesh=("Animals",)
            ),
            RecordLite(4, title="Missing abstract"),
        ]

    def representatives(self, dedup_result):
        by_id = {record.id: record for record in self.records}
        return [by_id[group.representative_id] for group in dedup_result.groups]

    def test_dedup_screen_pico_and_unchanged_rerun(self):
        result = self.dedup.run(self.records, run_id=1)
        records = self.representatives(result)
        self.assertEqual([record.id for record in records], [1, 3, 4])
        screened = self.screening.run(
            records, self.criteria, criteria_version_id=1, pico_terms=self.terms
        )
        decisions = {item.key.record_id: item.suggestion.decision for item in screened}
        self.assertEqual(decisions, {1: "include", 3: "exclude", 4: "maybe"})
        tagged = self.pico.run(records, decisions=decisions, pico_terms=self.terms)
        self.assertEqual([item.key.record_id for item in tagged], [1, 4])
        self.assertTrue(all(span.status == "unknown" for span in tagged[1].annotations))
        repeated_groups = self.dedup.run(self.records, run_id=2)
        self.assertEqual(result.groups, repeated_groups.groups)
        self.assertTrue(
            all(
                item.cached
                for item in self.screening.run(
                    records,
                    self.criteria,
                    criteria_version_id=1,
                    pico_terms=self.terms,
                )
            )
        )
        self.assertTrue(
            all(
                item.cached
                for item in self.pico.run(records, decisions=decisions, pico_terms=self.terms)
            )
        )
        self.assertEqual(
            (len(self.repo.evaluations), len(self.repo.suggestions), len(self.repo.annotations)),
            (1, 3, 2),
        )

    def test_caller_preserves_human_exclusion_over_machine_include(self):
        human = HumanDecision(1, "exclude", 1, reason_text="Wrong study population")
        records = self.representatives(self.dedup.run(self.records, run_id=1))
        screened = self.screening.run(
            records,
            self.criteria,
            criteria_version_id=1,
            pico_terms=self.terms,
            human_decisions={1: human},
        )
        self.assertEqual(screened[0].suggestion.decision, "include")
        self.assertEqual(screened[0].stale_reasons, ())
        # The pipeline/decision layer resolves precedence, not the engine.
        effective = {item.key.record_id: item.suggestion.decision for item in screened}
        effective[human.record_id] = human.decision
        tagged = self.pico.run(records, decisions=effective, pico_terms=self.terms)
        self.assertEqual([item.key.record_id for item in tagged], [4])
        self.assertEqual(human.decision, "exclude")

    def test_saved_snapshots_keep_earlier_groups_after_workspace_change(self):
        first = self.dedup.run(self.records, run_id=1)
        second = self.dedup.run(
            self.records, run_id=2, pair_decisions=[PairDecision(1, 2, "reject")]
        )
        self.assertEqual(self.repo.snapshots[1], first.groups)
        self.assertEqual(first.groups[0].member_ids, (1, 2))
        self.assertEqual(second.groups[0].member_ids, (1,))
        self.assertEqual(second.groups[1].member_ids, (2,))


if __name__ == "__main__":
    unittest.main()
