from django.test import SimpleTestCase

from etl.deduplicator import OpenAlexMatcher, SciELODeduplicator
from etl.pipeline.strategies import get_strategy


def make_deduplicator(document_type):
    return SciELODeduplicator(get_strategy(document_type).rules)


def make_matcher(document_type):
    matcher = OpenAlexMatcher.__new__(OpenAlexMatcher)
    matcher.rules = get_strategy(document_type).rules
    return matcher


class DocumentRulesTests(SimpleTestCase):
    def test_unknown_document_type_raises(self):
        with self.assertRaises(ValueError):
            get_strategy("unknown")

    def test_article_fuzzy_requires_source_match(self):
        deduplicator = make_deduplicator("article")
        groups = deduplicator.find_duplicates(
            [
                {"type": "article", "title": "Same title", "publication_year": 2024},
                {"type": "article", "title": "Same title", "publication_year": 2024},
            ]
        )

        self.assertEqual(len(groups), 2)

    def test_preprint_fuzzy_does_not_require_source_match(self):
        deduplicator = make_deduplicator("preprint")
        groups = deduplicator.find_duplicates(
            [
                {"type": "preprint", "title": "Same preprint title", "publication_year": 2024},
                {"type": "preprint", "title": "Same preprint title", "publication_year": 2024},
            ]
        )

        self.assertEqual(len(groups), 1)

    def test_dataset_does_not_use_fuzzy_strategy(self):
        deduplicator = make_deduplicator("dataset")
        groups = deduplicator.find_duplicates(
            [
                {"type": "dataset", "title": "Same dataset title", "publication_year": 2024},
                {"type": "dataset", "title": "Same dataset title", "publication_year": 2024},
            ]
        )

        self.assertEqual(len(groups), 2)

    def test_book_chapter_isbn_requires_chapter_title_match(self):
        matcher = make_matcher("book-chapter")
        is_valid, confidence, details = matcher._validate_openalex_match(
            {
                "type": "book-chapter",
                "title": "Chapter about public health",
                "publication_year": 2024,
                "parent_book": {"ids": {"isbn": "978-65-00-00000-1"}},
            },
            {
                "title": "Completely different chapter",
                "publication_year": 2024,
                "biblio": {"isbn": "978-65-00-00000-1"},
            },
        )

        self.assertFalse(is_valid)
        self.assertEqual(confidence, "low_confidence")
        self.assertIn("chapter_title_too_low_for_isbn", " ".join(details["reasons"]))

    def test_book_accepts_isbn_with_matching_title(self):
        matcher = make_matcher("book")
        is_valid, confidence, _details = matcher._validate_openalex_match(
            {
                "type": "book",
                "title": "Public health in Brazil",
                "publication_year": 2024,
                "ids": {"isbn": "978-65-00-00000-1"},
            },
            {
                "title": "Public health in Brazil",
                "publication_year": 2024,
                "biblio": {"isbn": "978-65-00-00000-1"},
            },
        )

        self.assertTrue(is_valid)
        self.assertEqual(confidence, "high")
