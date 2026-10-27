import unittest
from dataclasses import replace

from app.engines.screening import screen
from app.engines.types import CriterionSpec, PicoTerms, RecordLite


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.record = RecordLite(
            1, title="Clinical trial", abstract="Adults with migraine received treatment alpha."
        )
        self.terms = PicoTerms(population=("migraine",), intervention=("treatment alpha",))

    def criterion(self, code, **kwargs):
        return CriterionSpec(1, code, reason="Review eligibility requirement", **kwargs)

    def suggest(self, code, *, record=None, **kwargs):
        return screen(record or self.record, [self.criterion(code, **kwargs)], self.terms)

    def test_population_intervention_support_include(self):
        self.assertEqual(screen(self.record, [], self.terms).decision, "include")

    def test_absent_keywords_never_exclude(self):
        self.assertEqual(
            screen(
                self.record, [], PicoTerms(population=("unrelated",), intervention=("missing",))
            ).decision,
            "maybe",
        )

    def test_no_abstract_is_maybe_even_with_exclusion_metadata(self):
        self.assertEqual(
            self.suggest(
                "case_report",
                record=replace(self.record, abstract=None, pub_types=("Case Reports",)),
            ).decision,
            "maybe",
        )

    def test_whitespace_abstract_is_missing(self):
        self.assertEqual(
            screen(replace(self.record, abstract="   "), [], self.terms).evidence[0].code,
            "no_abstract",
        )

    def test_language_metadata_exclusion(self):
        result = self.suggest("non_english", record=replace(self.record, language="fre"))
        self.assertEqual((result.decision, result.strength), ("exclude", "strong"))

    def test_english_metadata(self):
        self.assertEqual(
            self.suggest("non_english", record=replace(self.record, language="eng")).decision,
            "include",
        )

    def test_english_multilanguage_is_not_excluded(self):
        self.assertEqual(
            self.suggest("non_english", record=replace(self.record, language="eng;fre")).decision,
            "include",
        )

    def test_language_rule_exclusion(self):
        text = "Les resultats des analyses dans une etude pour cette maladie avec traitement chez adultes ont ete observes."
        result = self.suggest(
            "non_english", record=replace(self.record, abstract=text), detector="rule"
        )
        self.assertEqual((result.decision, result.strength), ("exclude", "weak"))
        self.assertEqual(result.evidence[0].source, "rule")

    def test_unknown_language_goes_to_maybe(self):
        self.assertEqual(
            self.suggest("non_english", record=replace(self.record, language="und")).decision,
            "maybe",
        )

    def test_language_rule_confident_english(self):
        text = "The patients and participants in this study were with migraine and received treatment alpha from the clinic."
        self.assertEqual(
            self.suggest(
                "non_english", record=replace(self.record, abstract=text), detector="rule"
            ).decision,
            "include",
        )

    def test_language_ambiguous_is_maybe(self):
        text = "The patients avec cette etude dans una estudio para los pacientes received treatment alpha for migraine."
        self.assertEqual(
            self.suggest(
                "non_english", record=replace(self.record, abstract=text), detector="rule"
            ).decision,
            "maybe",
        )

    def test_non_human_metadata(self):
        result = self.suggest("non_human", record=replace(self.record, mesh=("Animals", "Mice")))
        self.assertEqual((result.decision, result.strength), ("exclude", "strong"))

    def test_animals_and_humans_metadata_not_excluded(self):
        self.assertEqual(
            self.suggest(
                "non_human", record=replace(self.record, mesh=("Animals", "Humans"))
            ).decision,
            "include",
        )

    def test_non_human_rule_species(self):
        for term in ("rats", "mice", "murine", "porcine", "zebrafish", "in vitro", "cell line"):
            with self.subTest(term=term):
                result = self.suggest(
                    "non_human",
                    record=replace(
                        self.record, abstract=f"We studied {term} models using treatment alpha."
                    ),
                    detector="rule",
                )
                self.assertEqual((result.decision, result.strength), ("exclude", "weak"))

    def test_human_cues_suppress_animal_rule(self):
        result = self.suggest(
            "non_human",
            record=replace(
                self.record,
                abstract="Adults with migraine received treatment alpha. Rat results were compared with patients.",
            ),
            detector="rule",
        )
        self.assertEqual(result.decision, "include")

    def test_case_report_metadata(self):
        self.assertEqual(
            self.suggest(
                "case_report", record=replace(self.record, pub_types=("Case Reports",))
            ).strength,
            "strong",
        )

    def test_case_report_rules(self):
        for text in (
            "This case report describes treatment.",
            "We report a case of migraine.",
            "A 40-year-old received treatment.",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    self.suggest(
                        "case_report", record=replace(self.record, abstract=text), detector="rule"
                    ).strength,
                    "weak",
                )

    def test_simulation_rules(self):
        for text in (
            "A simulation",
            "An in silico experiment",
            "Monte Carlo methods",
            "A modelling study",
            "A modeling study",
            "A microsimulation",
            "A Markov model",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    self.suggest(
                        "simulation", record=replace(self.record, abstract=text), detector="rule"
                    ).decision,
                    "exclude",
                )

    def test_custom_exclusion(self):
        result = self.suggest("custom_keyword", params={"terms": ["migraine"]}, detector="rule")
        self.assertEqual((result.decision, result.criterion_id), ("exclude", 1))

    def test_custom_keyword_boundaries(self):
        self.assertEqual(
            self.suggest("custom_keyword", params={"terms": ["rat"]}, detector="rule").decision,
            "include",
        )

    def test_missing_custom_include_gives_maybe(self):
        self.assertEqual(
            self.suggest(
                "custom_keyword", kind="include", params={"terms": ["randomized"]}, detector="rule"
            ).decision,
            "maybe",
        )

    def test_matching_custom_include(self):
        self.assertEqual(
            self.suggest(
                "custom_keyword",
                kind="include",
                params={"include_terms": ["migraine"]},
                detector="rule",
            ).decision,
            "include",
        )

    def test_disabled_criterion_does_not_fire(self):
        self.assertEqual(
            self.suggest(
                "custom_keyword", params={"terms": ["migraine"]}, is_active=False
            ).decision,
            "include",
        )

    def test_metadata_only_does_not_run_rules(self):
        self.assertEqual(
            self.suggest(
                "simulation",
                record=replace(self.record, abstract="A simulation."),
                detector="metadata",
            ).decision,
            "maybe",
        )

    def test_metadata_takes_precedence(self):
        self.assertEqual(
            self.suggest(
                "case_report",
                record=replace(
                    self.record,
                    abstract="Adults with migraine received treatment alpha; case report.",
                    pub_types=("Journal Article",),
                ),
            ).decision,
            "include",
        )

    def test_strong_exclusion_selected_before_weak(self):
        criteria = [
            self.criterion("simulation", detector="rule"),
            CriterionSpec(2, "case_report", reason="Exclude single cases"),
        ]
        result = screen(
            replace(self.record, abstract="A simulation.", pub_types=("Case Reports",)),
            criteria,
            self.terms,
        )
        self.assertEqual(
            (result.criterion_id, result.strength, len(result.evidence)), (2, "strong", 2)
        )

    def test_manual_criterion_requires_review(self):
        self.assertEqual(self.suggest("custom_keyword", detector="manual_only").decision, "maybe")

    def test_unsupported_criterion_requires_review(self):
        self.assertEqual(self.suggest("unknown_code").decision, "maybe")

    def test_no_pico_terms_defaults_to_maybe(self):
        self.assertEqual(screen(self.record, [], PicoTerms()).decision, "maybe")

    def test_criterion_reason_required(self):
        with self.assertRaises(ValueError):
            CriterionSpec(1, "non_human")

    def test_criteria_order_does_not_change_output(self):
        criteria = [
            self.criterion("simulation"),
            CriterionSpec(2, "case_report", reason="Review criteria"),
        ]
        self.assertEqual(
            screen(self.record, criteria, self.terms),
            screen(self.record, list(reversed(criteria)), self.terms),
        )

    def test_keyword_parameters_cannot_be_mutated_by_caller(self):
        values = ["migraine"]
        criterion = self.criterion("custom_keyword", params={"terms": values})
        values.clear()
        self.assertEqual(screen(self.record, [criterion], self.terms).decision, "exclude")


if __name__ == "__main__":
    unittest.main()
