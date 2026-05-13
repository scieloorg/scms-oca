from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from etl.indexing.contracts import SilverDocument
from etl.pipeline.orchestrator import OpenSearchETLPipeline


class OrchestratorAliasTests(SimpleTestCase):
    @patch("etl.pipeline.orchestrator.get_strategy")
    @patch("etl.pipeline.orchestrator.OpenAlexMatcher")
    @patch("etl.pipeline.orchestrator.SciELODeduplicator")
    @patch("etl.pipeline.orchestrator.OpenSearchClient")
    def test_indexing_adds_public_alias_to_physical_silver_index(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _get_strategy_cls,
    ):
        client = Mock()
        client.client.bulk.return_value = {"errors": False}
        client_cls.return_value = client
        pipeline = OpenSearchETLPipeline(
            opensearch_url="http://opensearch:9200",
            public_alias="scientific_production",
        )
        doc = SilverDocument(
            doc_id="S001",
            type="article",
            publication_year=2024,
            title="Title",
        )

        indexed_count = pipeline._index_silver_documents([doc])

        self.assertEqual(indexed_count, 1)
        client.create_index.assert_called_once()
        client.add_alias.assert_called_once_with(
            "silver_article_2024",
            "scientific_production",
        )
        self.assertEqual(pipeline.indexed_index_names, {"silver_article_2024"})

    @patch("etl.pipeline.orchestrator.get_strategy")
    @patch("etl.pipeline.orchestrator.OpenAlexMatcher")
    @patch("etl.pipeline.orchestrator.SciELODeduplicator")
    @patch("etl.pipeline.orchestrator.OpenSearchClient")
    def test_fallback_doc_id_is_stable(
        self,
        _client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _get_strategy_cls,
    ):
        pipeline = OpenSearchETLPipeline(
            opensearch_url="http://opensearch:9200",
        )
        payload = {
            "title": "A deterministic title",
            "publication_year": 2024,
            "journal_title": "Journal",
        }

        first = pipeline._stable_fallback_doc_id(payload)
        second = pipeline._stable_fallback_doc_id(payload)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("doc_"))

    @patch("etl.pipeline.orchestrator.get_strategy")
    @patch("etl.pipeline.orchestrator.OpenAlexMatcher")
    @patch("etl.pipeline.orchestrator.SciELODeduplicator")
    @patch("etl.pipeline.orchestrator.OpenSearchClient")
    def test_indexing_partial_bulk_errors_propagates_exception(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _get_strategy_cls,
    ):
        client = Mock()
        client.client.bulk.return_value = {
            "errors": True,
            "items": [{"index": {"status": 500, "error": {"type": "err"}}}],
        }
        client_cls.return_value = client
        pipeline = OpenSearchETLPipeline(
            opensearch_url="http://opensearch:9200",
            public_alias="scientific_production",
        )
        doc = SilverDocument(
            doc_id="S001",
            type="article",
            publication_year=2024,
            title="Title",
        )

        with self.assertRaises(RuntimeError):
            pipeline._index_silver_documents([doc])

        client.add_alias.assert_not_called()

    @patch("etl.pipeline.orchestrator.get_strategy")
    @patch("etl.pipeline.orchestrator.OpenAlexMatcher")
    @patch("etl.pipeline.orchestrator.SciELODeduplicator")
    @patch("etl.pipeline.orchestrator.OpenSearchClient")
    def test_indexing_generic_bulk_errors_propagates_exception(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _get_strategy_cls,
    ):
        client = Mock()
        client.client.bulk.side_effect = RuntimeError("cluster down")
        client_cls.return_value = client
        pipeline = OpenSearchETLPipeline(
            opensearch_url="http://opensearch:9200",
            public_alias="scientific_production",
        )
        doc = SilverDocument(
            doc_id="S001",
            type="article",
            publication_year=2024,
            title="Title",
        )

        with self.assertRaises(RuntimeError):
            pipeline._index_silver_documents([doc])

        client.add_alias.assert_not_called()
