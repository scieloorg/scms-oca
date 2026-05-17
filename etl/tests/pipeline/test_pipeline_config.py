from django.core.exceptions import ValidationError
from django.test import TestCase

from etl.models import EtlPipelineConfig


class PipelineConfigMatchTests(TestCase):
    def test_matches_exact(self):
        config = EtlPipelineConfig(
            name="article",
            input_index="bronze_scielo_articles-000001",
            input_document_kind="article",
            default_document_type="article",
        )
        self.assertTrue(config.matches_input_index("bronze_scielo_articles-000001"))
        self.assertFalse(config.matches_input_index("bronze_scielo_books"))

    def test_matches_wildcard_glob(self):
        config = EtlPipelineConfig(
            name="article",
            input_index="bronze_scielo_articles*",
            input_document_kind="article",
            default_document_type="article",
        )
        self.assertTrue(config.matches_input_index("bronze_scielo_articles-000001"))
        self.assertTrue(config.matches_input_index("bronze_scielo_articles-000002"))
        self.assertTrue(config.matches_input_index("bronze_scielo_articles"))
        self.assertFalse(config.matches_input_index("bronze_scielo_books"))

    def test_matches_question_mark(self):
        config = EtlPipelineConfig(
            name="article",
            input_index="bronze_scielo_articles-00000?",
            input_document_kind="article",
            default_document_type="article",
        )
        self.assertTrue(config.matches_input_index("bronze_scielo_articles-000001"))
        self.assertTrue(config.matches_input_index("bronze_scielo_articles-000009"))
        self.assertFalse(config.matches_input_index("bronze_scielo_articles-000010"))


class PipelineConfigDocumentTypeTests(TestCase):
    def test_initial_configs_exist(self):
        self.assertEqual(
            list(EtlPipelineConfig.objects.order_by("id").values_list("name", flat=True)),
            ["article", "book", "book-chapter", "preprint", "dataset"],
        )

    def test_preprint_ignores_payload_type(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_preprint")
        result = config.document_type_for_payload({"type": "research-article"})
        self.assertEqual(result, "preprint")

    def test_dataset_ignores_payload_type(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_dataset")
        result = config.document_type_for_payload({"type": "research-article"})
        self.assertEqual(result, "dataset")

    def test_book(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_books", {"type": "book"})
        result = config.document_type_for_payload({"type": "book"})
        self.assertEqual(result, "book")

    def test_book_chapter(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_books", {"type": "book-chapter"})
        result = config.document_type_for_payload({"type": "book-chapter"})
        self.assertEqual(result, "book-chapter")

    def test_book_fallback(self):
        result = EtlPipelineConfig.objects.get_enabled_by_name("book").document_type_for_payload({})
        self.assertEqual(result, "book")

    def test_books_index_without_payload_type_is_ambiguous(self):
        with self.assertRaisesRegex(ValueError, "Multiple enabled ETL pipeline configs"):
            EtlPipelineConfig.objects.get_for_source("bronze_scielo_books")

    def test_article_alias_is_canonicalized(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles")
        result = config.document_type_for_payload({"type": "research-article"})
        self.assertEqual(result, "article")

    def test_article_review_alias_is_canonicalized(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles")
        result = config.document_type_for_payload({"type": "review"})
        self.assertEqual(result, "article")

    def test_article_fallback_default(self):
        result = EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles").document_type_for_payload({})
        self.assertEqual(result, "article")

    def test_unknown_index_raises(self):
        with self.assertRaises(ValueError):
            EtlPipelineConfig.objects.get_for_source("unknown_index")

    def test_clean_source_payload_unwraps_raw_data(self):
        payload = {
            "raw_data": {"type": "book-chapter"},
            "oca_indexed_at": "now",
        }
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_books", payload)
        result = config.document_type_for_payload(payload)
        self.assertEqual(result, "book-chapter")

    def test_book_part_alias_is_canonicalized(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_books", {"type": "book-part"})
        result = config.document_type_for_payload({"type": "book-part"})
        self.assertEqual(result, "book-chapter")

    def test_chapter_alias_is_canonicalized(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_books", {"type": "chapter"})
        result = config.document_type_for_payload({"type": "chapter"})
        self.assertEqual(result, "book-chapter")

    def test_to_rules_rejects_invalid_strategies(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles")
        config.rules = {**config.rules, "scielo_dedup_strategies": ["doi", "unknown"]}

        with self.assertRaises(ValidationError):
            config.to_rules()

    def test_to_rules_returns_editable_rules(self):
        config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles")
        config.rules = {**config.rules, "fuzzy_min_similarity": 0.91}

        self.assertEqual(config.to_rules()["fuzzy_min_similarity"], 0.91)
