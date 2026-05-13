from django.test import SimpleTestCase

from etl.pipeline.defaults import PipelineTarget, normalize_document_type
from etl.pipeline.strategies import get_strategy


class PipelineTargetTests(SimpleTestCase):
    def test_matches_bronze_index_with_glob(self):
        target = PipelineTarget(
            document_type="article",
            bronze_index="bronze_scielo_articles*",
            silver_index_pattern="silver_article_{year}",
            rules=get_strategy("article").rules,
        )

        self.assertTrue(target.matches_bronze_index("bronze_scielo_articles-000001"))
        self.assertFalse(target.matches_bronze_index("bronze_scielo_books"))

    def test_normalize_document_type(self):
        self.assertEqual(normalize_document_type("research-article"), "research-article")
        with self.assertRaisesRegex(ValueError, "document_type"):
            normalize_document_type(None)
