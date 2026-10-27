import unittest
from dataclasses import replace

from app.engines.types import CriterionSpec, PicoTerms, RecordLite
from app.services.deduplication_service import DeduplicationService, PairDecision
from app.services.pico_service import PicoService
from app.services.screening_service import HumanDecision, ScreeningService
from tests.fakes import MemoryRepository


class DeduplicationServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.service = DeduplicationService(self.repo)
        self.records = [
            RecordLite(index, title="Same study", year=2024, first_author="Smith J")
            for index in (1, 2, 3)
        ]

    def test_rerun_does_not_duplicate_machine_evaluation(self):
        first = self.service.run(self.records, run_id=1)
        second = self.service.run(list(reversed(self.records)), run_id=1)
        self.assertEqual(first, second)
        self.assertEqual((len(self.repo.evaluations), len(self.repo.snapshots)), (1, 1))

    def test_direct_reject_separates_pair(self):
        result = self.service.run(
            self.records[:2], run_id=1, pair_decisions=[PairDecision(1, 2, "reject")]
        )
        self.assertEqual([snapshot.member_ids for snapshot in result.groups], [(1,), (2,)])

    def test_manual_reject_survives_rerun(self):
        decisions = [PairDecision(1, 2, "reject")]
        first = self.service.run(self.records[:2], run_id=1, pair_decisions=decisions)
        second = self.service.run(self.records[:2], run_id=2, pair_decisions=decisions)
        self.assertEqual(first.groups, second.groups)

    def test_transitive_bypass_returns_conflict_and_path(self):
        result = self.service.run(
            self.records, run_id=1, pair_decisions=[PairDecision(1, 2, "reject")]
        )
        self.assertEqual(result.conflicts[0].path, (1, 3, 2))
        self.assertEqual(result.conflicts[0].kind, "pair_override_bypassed")
        rerun = self.service.run(
            self.records, run_id=2, pair_decisions=[PairDecision(1, 2, "reject")]
        )
        self.assertEqual(result.conflicts[0].fingerprint, rerun.conflicts[0].fingerprint)

    def test_human_confirm_connects_uncertain_pair(self):
        records = [self.records[0], replace(self.records[1], first_author=None)]
        automatic = self.service.run(records, run_id=1)
        confirmed = self.service.run(
            records, run_id=2, pair_decisions=[PairDecision(2, 1, "confirm")]
        )
        self.assertEqual(len(automatic.groups), 2)
        self.assertEqual(confirmed.groups[0].member_ids, (1, 2))

    def test_old_machine_edge_not_reused_after_metadata_changes(self):
        self.service.run(self.records[:2], run_id=1)
        changed = [self.records[0], replace(self.records[1], title="Entirely different report")]
        result = self.service.run(changed, run_id=2)
        self.assertEqual(len(result.groups), 2)
        self.assertEqual(len(self.repo.evaluations), 2)

    def test_pinned_representative(self):
        result = self.service.run(self.records, run_id=1, pinned_record_ids=[3])
        self.assertEqual(result.groups[0].representative_id, 3)

    def test_inactive_decision_does_not_add_records(self):
        result = self.service.run(
            self.records[:1], run_id=1, pair_decisions=[PairDecision(1, 99, "confirm")]
        )
        self.assertEqual(result.groups[0].member_ids, (1,))

    def test_duplicate_current_pair_decisions_rejected(self):
        with self.assertRaises(ValueError):
            self.service.run(
                self.records,
                run_id=1,
                pair_decisions=[PairDecision(1, 2, "confirm"), PairDecision(2, 1, "reject")],
            )

    def test_existing_snapshot_cannot_be_rewritten(self):
        self.service.run(self.records, run_id=1)
        with self.assertRaises(ValueError):
            self.service.run(self.records[:1], run_id=1)


class ScreeningServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.service = ScreeningService(self.repo)
        self.record = RecordLite(1, abstract="Patients with migraine received compound x.")
        self.terms = PicoTerms(population=("migraine",), intervention=("compound x",))

    def run_service(self, record=None, criteria=None, version=1, terms=None, decisions=None):
        return self.service.run(
            [record or self.record],
            criteria or [],
            criteria_version_id=version,
            pico_terms=terms or self.terms,
            human_decisions=decisions,
        )[0]

    def test_idempotent_and_cached(self):
        self.assertFalse(self.run_service().cached)
        self.assertTrue(self.run_service().cached)
        self.assertEqual(len(self.repo.suggestions), 1)

    def test_new_metadata_invalidates_even_if_source_hash_is_unchanged(self):
        record = replace(self.record, content_hash="upstream-constant")
        self.run_service(record=record)
        self.assertFalse(self.run_service(record=replace(record, language="fre")).cached)
        self.assertEqual(len(self.repo.suggestions), 2)

    def test_new_criteria_version_invalidates(self):
        self.run_service()
        self.assertFalse(self.run_service(version=2).cached)

    def test_changed_pico_terms_invalidate(self):
        self.run_service()
        result = self.run_service(
            terms=PicoTerms(population=("unrelated",), intervention=("unrelated",))
        )
        self.assertFalse(result.cached)
        self.assertEqual(result.suggestion.decision, "maybe")

    def test_changed_parameters_invalidate(self):
        first = CriterionSpec(
            1, "custom_keyword", reason="Criterion", params={"terms": ["unrelated"]}
        )
        second = CriterionSpec(
            1, "custom_keyword", reason="Criterion", params={"terms": ["migraine"]}
        )
        self.run_service(criteria=[first])
        result = self.run_service(criteria=[second])
        self.assertFalse(result.cached)
        self.assertEqual(result.suggestion.decision, "exclude")

    def test_removed_criterion_and_disagreement_flagged_without_changing_decision(self):
        decision = HumanDecision(1, "exclude", 1, criterion_id=99)
        decisions = {1: decision}
        result = self.run_service(version=2, decisions=decisions)
        self.assertEqual(
            result.stale_reasons, ("criterion_removed_or_inactive", "suggestion_disagrees")
        )
        self.assertEqual(decisions[1], decision)
        self.assertEqual(self.repo.human_decisions, {1: "exclude"})

    def test_same_decision_new_criteria_version_not_automatically_stale(self):
        result = self.run_service(version=2, decisions={1: HumanDecision(1, "include", 1)})
        self.assertEqual(result.stale_reasons, ())

    def test_deliberate_override_of_current_suggestion_is_not_stale(self):
        result = self.run_service(
            decisions={1: HumanDecision(1, "exclude", 1, reason_text="Reviewer assessment")}
        )
        self.assertEqual(result.stale_reasons, ())

    def test_changed_content_can_flag_disagreement_with_same_criteria_version(self):
        decision = HumanDecision(
            1, "exclude", 1, reason_text="Reviewer assessment", content_hash="older-input"
        )
        result = self.run_service(decisions={1: decision})
        self.assertEqual(result.stale_reasons, ("suggestion_disagrees",))

    def test_changed_terms_can_flag_disagreement_with_same_criteria_version(self):
        decision = HumanDecision(
            1, "exclude", 1, reason_text="Reviewer assessment", context_hash="older-context"
        )
        result = self.run_service(decisions={1: decision})
        self.assertEqual(result.stale_reasons, ("suggestion_disagrees",))

    def test_exclusion_reason_required(self):
        with self.assertRaises(ValueError):
            HumanDecision(1, "exclude", 1, reason_text=" ")

    def test_empty_inputs(self):
        self.assertEqual(self.service.run([], [], criteria_version_id=1, pico_terms=self.terms), ())


class PicoServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.service = PicoService(self.repo)
        self.record = RecordLite(1, abstract="Patients with migraine received compound x.")

    def run_service(self, record=None, terms=None, decision="include"):
        return self.service.run(
            [record or self.record], decisions={1: decision}, pico_terms=terms or PicoTerms()
        )

    def test_annotation_batches_are_idempotent(self):
        self.assertFalse(self.run_service()[0].cached)
        self.assertTrue(self.run_service()[0].cached)
        self.assertEqual(len(self.repo.annotations), 1)

    def test_missing_abstract_unknown_batch_is_cached(self):
        record = replace(self.record, abstract=None)
        first = self.run_service(record=record)[0]
        self.assertTrue(all(span.status == "unknown" for span in first.annotations))
        self.assertTrue(self.run_service(record=record)[0].cached)

    def test_abstract_changes_invalidate(self):
        self.run_service()
        self.assertFalse(
            self.run_service(record=replace(self.record, abstract="Received compound y."))[0].cached
        )

    def test_review_terms_changes_invalidate(self):
        self.run_service()
        self.assertFalse(self.run_service(terms=PicoTerms(intervention=("compound x",)))[0].cached)

    def test_excluded_and_unscreened_records_skipped(self):
        self.assertEqual(self.run_service(decision="exclude"), ())
        self.assertEqual(self.service.run([self.record], decisions={}, pico_terms=PicoTerms()), ())

    def test_maybe_records_processed(self):
        self.assertEqual(len(self.run_service(decision="maybe")), 1)

    def test_human_annotations_untouched(self):
        self.run_service()
        self.assertEqual(self.repo.human_annotations, {1: "Reviewer-corrected population"})


if __name__ == "__main__":
    unittest.main()
