from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from etl.indexing.contracts import SilverDocument
from etl.pipeline.defaults import PipelineTarget
from etl.pipeline.orchestrator import SilverETLPipeline


def make_target():
    return PipelineTarget(
        document_type="article",
        source_index="bronze_scielo_articles",
        silver_index_pattern="silver_article_{year}",
    )


class SilverETLPipelineTests(SimpleTestCase):
    @override_settings(ETL_PUBLIC_ALIAS="scientific_production", ETL_DEFAULT_BATCH_SIZE=1000)
    @patch("etl.pipeline.orchestrator.OpenSearchIndexClient")
    def test_indexing_adds_public_alias_to_physical_silver_index(self, client_cls):
        client = Mock()
        client.client.bulk.return_value = {"errors": False}
        client_cls.return_value = client
        pipeline = SilverETLPipeline(make_target(), opensearch_url="http://opensearch:9200")
        doc = SilverDocument(
            doc_id="S1",
            type="article",
            publication_year=2024,
            title="Title",
        )

        indexed_count = pipeline._index_silver_documents([doc])

        self.assertEqual(indexed_count, 1)
        client.create_index.assert_called_once()
        client.add_alias.assert_called_once_with("silver_article_2024", "scientific_production")
        self.assertEqual(pipeline.indexed_index_names, {"silver_article_2024"})

    @patch("etl.pipeline.orchestrator.OpenSearchIndexClient")
    def test_stable_fallback_doc_id_is_deterministic(self, client_cls):
        client_cls.return_value = Mock()
        pipeline = SilverETLPipeline(make_target(), opensearch_url="http://opensearch:9200")
        payload = {"title": "A deterministic title", "publication_year": 2024}

        self.assertEqual(
            pipeline._stable_fallback_doc_id(payload),
            pipeline._stable_fallback_doc_id(payload),
        )

    @patch("etl.pipeline.orchestrator.OpenSearchIndexClient")
    def test_bulk_errors_fail_indexing(self, client_cls):
        client = Mock()
        client.client.bulk.return_value = {
            "errors": True,
            "items": [{"index": {"status": 500, "error": {"type": "err"}}}],
        }
        client_cls.return_value = client
        pipeline = SilverETLPipeline(make_target(), opensearch_url="http://opensearch:9200")
        doc = SilverDocument(
            doc_id="S1",
            type="article",
            publication_year=2024,
            title="Title",
        )

        with self.assertRaisesRegex(RuntimeError, "Bulk indexing failed"):
            pipeline._index_silver_documents([doc])

        client.add_alias.assert_not_called()
