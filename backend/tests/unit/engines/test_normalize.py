import unittest

from app.engines.normalize import (
    normalize_author,
    normalize_doi,
    normalize_journal,
    normalize_pmid,
    normalize_title,
)


class NormalizeTests(unittest.TestCase):
    def test_doi_variants(self):
        variants = (
            "10.1000/ABC",
            "https://doi.org/10.1000/ABC",
            "http://doi.org/10.1000/abc",
            "http://dx.doi.org/10.1000/abc",
            "DOI: 10.1000/ABC",
            " 10.1000/abc. ",
            "https://doi.org/10.1000%2FABC",
            "10.1000 / abc;",
        )
        for value in variants:
            with self.subTest(value=value):
                self.assertEqual(normalize_doi(value), "10.1000/abc")

    def test_doi_balanced_parentheses_are_preserved(self):
        self.assertEqual(normalize_doi("10.1000/a(12)"), "10.1000/a(12)")

    def test_doi_citation_parenthesis_is_removed(self):
        self.assertEqual(normalize_doi("10.1000/a(12))."), "10.1000/a(12)")

    def test_invalid_doi_does_not_match_as_identifier(self):
        for value in (None, "", "not a doi", "10.1/a", "https://example.org/10.1000/a"):
            with self.subTest(value=value):
                self.assertIsNone(normalize_doi(value))

    def test_pmid_normalization(self):
        for value in (
            12345,
            "12345",
            " 00012345 ",
            "PMID:12345",
            "https://pubmed.ncbi.nlm.nih.gov/12345/",
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_pmid(value), "12345")

    def test_invalid_pmid(self):
        for value in (None, "", "0", True, "PMID 12 and 34", "12-34", "-12"):
            with self.subTest(value=value):
                self.assertIsNone(normalize_pmid(value))

    def test_title_unicode_punctuation_whitespace(self):
        self.assertEqual(normalize_title("  Étude: ＡＢＣ—Trial.\n"), "etude abc trial")

    def test_title_non_latin_text_survives(self):
        self.assertEqual(normalize_title("研究：结果。"), "研究 结果")

    def test_author_initials_and_accents(self):
        self.assertEqual(normalize_author("García JA"), "garcia")
        self.assertEqual(normalize_author("García, Juan"), "garcia")
        self.assertEqual(normalize_author("van der Meer J."), "van der meer")

    def test_journal(self):
        self.assertEqual(normalize_journal("J. Clinical-Medicine"), "j clinical medicine")

    def test_missing_text(self):
        self.assertEqual(normalize_title(None), "")
        self.assertEqual(normalize_author(None), "")


if __name__ == "__main__":
    unittest.main()
