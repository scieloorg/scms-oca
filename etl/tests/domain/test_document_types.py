from django.test import SimpleTestCase, TestCase, override_settings

from etl.models import EtlPipelineConfig
from etl.transform.normalizers import normalize_document_type_for_etl, normalize_text


class DocumentTypeTests(SimpleTestCase):
    def test_normalize_document_type_for_etl_normalizes_input(self):
        self.assertEqual(normalize_document_type_for_etl("research-article"), "article")
        self.assertEqual(normalize_document_type_for_etl("book_part"), "book-chapter")
        with self.assertRaisesRegex(ValueError, "document_type"):
            normalize_document_type_for_etl(None)

    def test_normalize_text_still_handles_generic_text(self):
        self.assertEqual(normalize_text("  Sa\u00fade   p\u00fablica  "), "Saude publica")

    def test_normalize_document_type_for_etl_uses_settings_aliases(self):
        self.assertEqual(normalize_document_type_for_etl("research-article"), "article")
        self.assertEqual(normalize_document_type_for_etl("book-part"), "book-chapter")
        self.assertEqual(normalize_document_type_for_etl("chapter"), "book-chapter")

    @override_settings(ETL_DOCUMENT_TYPE_ALIAS={"foo": "article"})
    def test_normalize_document_type_for_etl_accepts_settings_override(self):
        self.assertEqual(normalize_document_type_for_etl("foo"), "article")
        self.assertEqual(normalize_document_type_for_etl("research-article"), "research-article")


class PipelineConfigDefaultsTests(TestCase):
    def test_migration_creates_initial_pipeline_configs(self):
        self.assertEqual(EtlPipelineConfig.objects.count(), 5)
        self.assertTrue(EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles").deduplicate_scielo)
        self.assertFalse(EtlPipelineConfig.objects.get_for_source("bronze_scielo_preprint").deduplicate_scielo)

    def test_initial_config_generates_equivalent_rules(self):
        article_rules = EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles").to_rules()

        self.assertEqual(article_rules["document_type"], "article")
        self.assertEqual(article_rules["scielo_dedup_strategies"], ["doi", "pid", "fuzzy"])
        self.assertEqual(article_rules["openalex_match_strategies"], ["doi", "isbn", "title"])
