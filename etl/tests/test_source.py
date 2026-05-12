from django.test import SimpleTestCase

from etl.defaults import PipelineTarget, get_pipeline_target
from etl.strategies import get_strategy


class PipelineTargetMatchTests(SimpleTestCase):
    def test_matches_exact(self):
        target = PipelineTarget(
            "article",
            "bronze_scielo_articles-000001",
            "silver_article_{year}",
            get_strategy("article").rules,
        )
        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles-000001"))
        self.assertFalse(target.matches_bronze_index("bronze_scielo_books"))

    def test_matches_wildcard_glob(self):
        target = PipelineTarget(
            "article",
            "bronze_scielo_articles*",
            "silver_article_{year}",
            get_strategy("article").rules,
        )
        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles-000001"))
        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles-000002"))
        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles"))
        self.assertFalse(target.matches_bronze_index("bronze_scielo_books"))

    def test_matches_question_mark(self):
        target = PipelineTarget(
            "article",
            "bronze_scielo_articles-00000?",
            "silver_article_{year}",
            get_strategy("article").rules,
        )
        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles-000001"))
        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles-000009"))
        self.assertFalse(target.matches_bronze_index("bronze_scielo_articles-000010"))


class PipelineTargetDocumentTypeTests(SimpleTestCase):
    def test_preprint(self):
        result = get_pipeline_target("bronze_scielo_preprint").document_type_for(
            {"type": "research-article"}
        )
        self.assertEqual(result, "preprint")

    def test_dataset(self):
        result = get_pipeline_target("bronze_scielo_dataset").document_type_for({})
        self.assertEqual(result, "dataset")

    def test_book(self):
        result = get_pipeline_target("bronze_scielo_books").document_type_for({"type": "book"})
        self.assertEqual(result, "book")

    def test_book_chapter(self):
        result = get_pipeline_target("bronze_scielo_books").document_type_for(
            {"type": "book-chapter"}
        )
        self.assertEqual(result, "book-chapter")

    def test_book_fallback(self):
        result = get_pipeline_target("bronze_scielo_books").document_type_for({})
        self.assertEqual(result, "book")

    def test_article_exact(self):
        result = get_pipeline_target("bronze_scielo_articles-000001").document_type_for(
            {"type": "research-article"}
        )
        self.assertEqual(result, "research-article")

    def test_article_fallback_from_payload(self):
        result = get_pipeline_target("bronze_scielo_articles-000001").document_type_for(
            {"type": "review"}
        )
        self.assertEqual(result, "review")

    def test_article_fallback_default(self):
        result = get_pipeline_target("bronze_scielo_articles-000001").document_type_for({})
        self.assertEqual(result, "article")

    def test_unknown_index_raises(self):
        with self.assertRaises(ValueError):
            get_pipeline_target("unknown_index")

    def test_unknown_index_without_type_raises(self):
        with self.assertRaises(ValueError):
            get_pipeline_target("unknown_index")

    def test_clean_source_payload_unwraps_raw_data(self):
        result = get_pipeline_target("bronze_scielo_books").document_type_for(
            {
                "raw_data": {"type": "book-chapter"},
                "oca_indexed_at": "now",
            }
        )
        self.assertEqual(result, "book-chapter")

    def test_wildcard_articles_match(self):
        target = PipelineTarget(
            "article",
            "bronze_scielo_articles*",
            "silver_article_{year}",
            get_strategy("article").rules,
        )
        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles-000002"))
