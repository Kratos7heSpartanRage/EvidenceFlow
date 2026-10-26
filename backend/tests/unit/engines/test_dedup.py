import unittest
from dataclasses import replace

from app.engines.dedup import group, group_key, representative, score_pairs
from app.engines.types import RecordLite


class DedupTests(unittest.TestCase):
    def setUp(self):
        self.a = RecordLite(1, title="A randomized study of treatment", year=2024, first_author="Smith J")
        self.b = replace(self.a, id=2)

    def pair(self, **changes):
        return score_pairs([self.a, replace(self.b, **changes)])[0]

    def test_exact_doi(self):
        result = score_pairs([replace(self.a, doi="DOI:10.1000/A"), replace(self.b, doi="https://doi.org/10.1000/a")])[0]
        self.assertEqual((result.method, result.tier, result.score), ("doi", "auto", 1.0))

    def test_cross_source_pmid(self):
        result = score_pairs([replace(self.a, source="pubmed", pmid="123"), replace(self.b, source="europe_pmc", pmid=123)])[0]
        self.assertEqual((result.method, result.tier), ("pmid", "auto"))

    def test_title_year_author(self):
        self.assertEqual((self.pair().tier, self.pair().score), ("auto", 0.95))

    def test_author_list_fallback(self):
        result = score_pairs([replace(self.a, first_author=None, authors=("Smith J",)), self.b])[0]
        self.assertEqual(result.tier, "auto")

    def test_missing_author_is_uncertain(self):
        self.assertEqual(self.pair(first_author=None).tier, "uncertain")

    def test_conflicting_author_is_uncertain(self):
        result = self.pair(first_author="Jones S")
        self.assertEqual(result.tier, "uncertain")
        self.assertIn("first_author", result.conflicting_fields)

    def test_adjacent_year_is_not_blocked_out(self):
        self.assertEqual(self.pair(year=2025).tier, "uncertain")

    def test_distant_year_without_identifier_is_not_duplicate(self):
        self.assertEqual(score_pairs([self.a, replace(self.b, year=2027)]), [])

    def test_missing_year_is_uncertain(self):
        self.assertEqual(self.pair(year=None).tier, "uncertain")

    def test_different_dois_are_uncertain(self):
        result = score_pairs([replace(self.a, doi="10.1000/a"), replace(self.b, doi="10.1000/b")])[0]
        self.assertEqual(result.tier, "uncertain")
        self.assertIn("doi", result.conflicting_fields)

    def test_same_pmid_with_conflicting_doi_is_uncertain(self):
        result = score_pairs([replace(self.a, doi="10.1000/a", pmid="123"), replace(self.b, doi="10.1000/b", pmid="123")])[0]
        self.assertEqual(result.tier, "uncertain")

    def test_conference_journal_guard(self):
        result = score_pairs([replace(self.a, pub_types=("Congress",)), replace(self.b, pub_types=("Journal Article",))])[0]
        self.assertEqual(result.tier, "uncertain")
        self.assertIn("publication_type", result.conflicting_fields)

    def test_conference_guard_even_with_exact_doi(self):
        result = score_pairs([replace(self.a, doi="10.1000/a", pub_types=("Meeting Abstract",)), replace(self.b, doi="10.1000/a", pub_types=("Journal Article",))])[0]
        self.assertEqual(result.tier, "uncertain")

    def test_empty_identifiers_and_titles_do_not_match(self):
        self.assertEqual(score_pairs([RecordLite(1), RecordLite(2)]), [])

    def test_invalid_identifiers_do_not_match(self):
        self.assertEqual(score_pairs([RecordLite(1, doi="unknown", pmid="n/a"), RecordLite(2, doi="unknown", pmid="n/a")]), [])

    def test_fuzzy_is_opt_in_and_uncertain(self):
        title = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
        records = [RecordLite(1, title=title, year=2024), RecordLite(2, title="kappa iota theta eta zeta epsilon delta gamma beta alpha", year=2024)]
        self.assertEqual(score_pairs(records), [])
        result = score_pairs(records, include_fuzzy=True)[0]
        self.assertEqual((result.method, result.tier), ("fuzzy", "uncertain"))

    def test_incremental_filter(self):
        records = [self.a, self.b, replace(self.a, id=3)]
        self.assertEqual([(p.record_a_id, p.record_b_id) for p in score_pairs(records, changed_ids={3})], [(1, 3), (2, 3)])
        self.assertEqual(score_pairs(records, changed_ids=set()), [])

    def test_output_stable_when_input_order_changes(self):
        self.assertEqual(score_pairs([self.a, self.b]), score_pairs([self.b, self.a]))

    def test_duplicate_record_ids_rejected(self):
        with self.assertRaises(ValueError):
            score_pairs([self.a, self.a])

    def test_changed_ids_outside_scope_rejected(self):
        with self.assertRaises(ValueError):
            score_pairs([self.a], changed_ids={99})

    def test_group_includes_singletons(self):
        self.assertEqual(group([1, 2, 3, 4], [(1, 2), (2, 3)]), [{1, 2, 3}, {4}])

    def test_empty_groups(self):
        self.assertEqual(group([], []), [])

    def test_invalid_edges_rejected(self):
        for edges in ([(1, 99)], [(1, 1)]):
            with self.subTest(edges=edges), self.assertRaises(ValueError):
                group([1, 2], edges)

    def test_representative_preference_and_pin(self):
        values = [self.a, replace(self.b, abstract="Text"), replace(self.a, id=3, abstract="Text", doi="10.1000/a", source="pubmed")]
        self.assertEqual(representative(values), 3)
        self.assertEqual(representative(values, pinned_ids={1}), 1)

    def test_group_key_stable(self):
        self.assertEqual(group_key([3, 1, 2]), group_key([2, 1, 3]))
        self.assertNotEqual(group_key([1, 2]), group_key([1, 3]))


if __name__ == "__main__":
    unittest.main()
