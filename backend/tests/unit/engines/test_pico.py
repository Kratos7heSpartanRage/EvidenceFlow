import unittest

from app.engines.pico import extract_pico
from app.engines.types import PicoTerms


class PicoTests(unittest.TestCase):
    def suggestions(self, text, label, terms=None):
        return [
            span
            for span in extract_pico(text, terms or PicoTerms())
            if span.label == label and span.status == "suggested"
        ]

    def test_population_cues(self):
        for text in (
            "Patients with asthma were enrolled.",
            "Adults with diabetes participated.",
            "Children aged 12 participated.",
            "120 participants enrolled.",
            "Women who volunteered were included.",
            "Subjects with asthma enrolled.",
        ):
            with self.subTest(text=text):
                self.assertTrue(self.suggestions(text, "P"))

    def test_intervention_cues(self):
        for text in (
            "Randomized to therapy.",
            "Randomised to therapy.",
            "Received therapy.",
            "Treated with therapy.",
            "Administration of therapy.",
        ):
            with self.subTest(text=text):
                self.assertTrue(self.suggestions(text, "I"))

    def test_comparator_cues(self):
        for text in (
            "Therapy versus usual care.",
            "Therapy vs. placebo.",
            "Compared with standard care.",
            "Compared to sham.",
            "The control group received water.",
        ):
            with self.subTest(text=text):
                self.assertTrue(self.suggestions(text, "C"))

    def test_outcome_cues(self):
        for text in (
            "Primary outcome was weight.",
            "Secondary outcome was pain.",
            "Measured blood pressure.",
            "Change in weight was recorded.",
            "Incidence of relapse fell.",
            "Mortality was measured.",
        ):
            with self.subTest(text=text):
                self.assertTrue(self.suggestions(text, "O"))

    def test_unknown_comparator_never_fabricated(self):
        spans = [
            span
            for span in extract_pico("Patients with asthma received therapy.", PicoTerms())
            if span.label == "C"
        ]
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            (spans[0].status, spans[0].text, spans[0].start_char, spans[0].end_char),
            ("unknown", None, None, None),
        )

    def test_empty_abstract_four_unknown_labels(self):
        for text in (None, "", "   "):
            with self.subTest(text=text):
                result = extract_pico(text, PicoTerms())
                self.assertEqual([span.label for span in result], list("PICO"))
                self.assertTrue(all(span.status == "unknown" for span in result))

    def test_unicode_offsets_slice_original_text(self):
        text = (
            "😀 Étude. Patients with café sensitivity received β-therapy; primary outcome was pain."
        )
        for span in extract_pico(text, PicoTerms()):
            if span.status == "suggested":
                self.assertEqual(text[span.start_char : span.end_char], span.text)

    def test_review_lexicon_all_labels(self):
        terms = PicoTerms(("migraine",), ("compound x",), ("saline",), ("headache days",))
        text = "Migraine improved after compound x versus saline. Headache days declined."
        self.assertTrue(all(self.suggestions(text, label, terms) for label in "PICO"))

    def test_maximum_twelve_tokens(self):
        text = "Patients with " + " ".join(f"word{index}" for index in range(30)) + "."
        self.assertEqual(len(self.suggestions(text, "P")[0].text.split()), 12)

    def test_semicolon_stops_span(self):
        self.assertEqual(
            self.suggestions("Received therapy; follow-up occurred later.", "I")[0].text,
            "Received therapy",
        )

    def test_next_label_stops_previous_span(self):
        text = (
            "Patients with asthma received therapy, compared with placebo; mortality was measured."
        )
        self.assertEqual(self.suggestions(text, "P")[0].text, "Patients with asthma")
        self.assertEqual(self.suggestions(text, "I")[0].text, "received therapy")

    def test_repeated_cues_have_distinct_offsets(self):
        result = self.suggestions("Received therapy. Received water.", "I")
        self.assertEqual(len(result), 2)
        self.assertNotEqual(result[0].start_char, result[1].start_char)

    def test_review_term_does_not_match_substring(self):
        self.assertFalse(
            self.suggestions("We tested rating scales.", "I", PicoTerms(intervention=("rat",)))
        )

    def test_output_deterministic(self):
        text = "Patients with asthma received therapy compared with placebo."
        self.assertEqual(extract_pico(text, PicoTerms()), extract_pico(text, PicoTerms()))

    def test_explicitly_absent_comparator_is_unknown(self):
        for text in (
            "There was no control group.",
            "This trial proceeded without a control group.",
        ):
            with self.subTest(text=text):
                self.assertFalse(self.suggestions(text, "C"))

    def test_unreported_outcome_is_unknown(self):
        self.assertFalse(self.suggestions("The primary outcome was not reported.", "O"))

    def test_cue_without_value_is_unknown(self):
        for label, text in (("P", "Patients with."), ("I", "Received."), ("O", "Primary outcome.")):
            with self.subTest(label=label):
                self.assertFalse(self.suggestions(text, label))

    def test_negative_outcome_can_still_be_annotated(self):
        self.assertTrue(self.suggestions("There was no change in pain.", "O"))

    def test_overlapping_same_label_cues_do_not_duplicate(self):
        result = self.suggestions(
            "Patients with asthma enrolled.", "P", PicoTerms(population=("asthma",))
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "Patients with asthma enrolled")

    def test_review_terms_do_not_split_cue_from_its_value(self):
        text = "Patients with migraine received compound x compared with placebo. The primary outcome was headache days."
        terms = PicoTerms(("migraine",), ("compound x",), ("placebo",), ("headache days",))
        spans = {label: self.suggestions(text, label, terms) for label in "PICO"}
        self.assertEqual(spans["P"][0].text, "Patients with migraine")
        self.assertEqual(spans["I"][0].text, "received compound x")
        self.assertEqual(spans["C"][0].text, "compared with placebo")
        self.assertEqual(spans["O"][0].text, "primary outcome was headache days")
        self.assertTrue(all(len(values) == 1 for values in spans.values()))


if __name__ == "__main__":
    unittest.main()
