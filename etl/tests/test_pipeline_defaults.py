from django.test import SimpleTestCase

from etl.pipeline.defaults import PipelineTarget, normalize_document_type


class PipelineTargetTests(SimpleTestCase):
    def test_matches_source_index_with_glob(self):
        target = PipelineTarget(
            document_type="article",
            source_index="bronze_scielo_articles*",
            silver_index_pattern="silver_article_{year}",
        )

        self.assertTrue(target.matches_source_index("bronze_scielo_articles-000001"))
        self.assertFalse(target.matches_source_index("bronze_scielo_books"))

    def test_silver_index_name_requires_year_for_partitioned_patterns(self):
        target = PipelineTarget(
            document_type="article",
            source_index="bronze_scielo_articles",
            silver_index_pattern="silver_article_{year}",
        )

        self.assertEqual(target.silver_index_name(2024), "silver_article_2024")
        with self.assertRaisesRegex(ValueError, "publication_year"):
            target.silver_index_name(None)

    def test_silver_index_name_accepts_unpartitioned_index(self):
        target = PipelineTarget(
            document_type="dataset",
            source_index="bronze_scielo_dataset",
            silver_index_pattern="silver_dataset",
        )

        self.assertEqual(target.silver_index_name(None), "silver_dataset")

    def test_normalize_document_type(self):
        self.assertEqual(normalize_document_type("book_chapter"), "book-chapter")
        with self.assertRaisesRegex(ValueError, "document_type"):
            normalize_document_type(None)
