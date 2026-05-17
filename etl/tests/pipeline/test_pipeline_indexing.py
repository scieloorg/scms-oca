from unittest.mock import Mock, patch

from django.test import TestCase

from etl.documents import SilverDocument
from etl.mapping_silver import SILVER_MAPPING
from etl.pipeline import OpenSearchETLPipeline


class OrchestratorAliasTests(TestCase):
    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_indexing_adds_public_alias_to_physical_silver_index(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _standardizer_for,
    ):
        client = Mock()
        client.client.bulk.return_value = {"errors": False}
        client.ensure_rollover_index.return_value = "silver_scientific_production-000001"
        client.rollover.return_value = None
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
        client.ensure_rollover_index.assert_called_once_with(
            index_prefix="silver_scientific_production",
            write_alias="silver_write",
            public_alias="scientific_production",
            mapping=SILVER_MAPPING,
        )
        client.rollover.assert_called_once()
        client.add_alias.assert_not_called()
        self.assertEqual(pipeline.indexed_index_names, {"silver_scientific_production-000001"})

    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_indexing_multiple_years_uses_single_silver_index(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _standardizer_for,
    ):
        client = Mock()
        client.client.bulk.return_value = {"errors": False}
        client.ensure_rollover_index.return_value = "silver_scientific_production-000001"
        client.rollover.return_value = None
        client_cls.return_value = client
        pipeline = OpenSearchETLPipeline(
            opensearch_url="http://opensearch:9200",
            public_alias="scientific_production",
        )
        docs = [
            SilverDocument(doc_id="S001", type="article", publication_year=2023, title="Title 1"),
            SilverDocument(doc_id="S002", type="article", publication_year=2024, title="Title 2"),
        ]

        indexed_count = pipeline._index_silver_documents(docs)

        self.assertEqual(indexed_count, 2)
        client.ensure_rollover_index.assert_called_once()
        bulk_body = client.client.bulk.call_args.kwargs["body"]
        self.assertEqual(bulk_body[0]["index"]["_index"], "silver_write")
        self.assertEqual(bulk_body[2]["index"]["_index"], "silver_write")
        client.add_alias.assert_not_called()
        self.assertEqual(pipeline.indexed_index_names, {"silver_scientific_production-000001"})

    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_indexing_skips_documents_without_publication_year(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _standardizer_for,
    ):
        client_cls.return_value = Mock()
        pipeline = OpenSearchETLPipeline(
            opensearch_url="http://opensearch:9200",
        )
        doc = SilverDocument(doc_id="S001", type="article", title="Title")

        indexed_count = pipeline._index_silver_documents([doc])

        self.assertEqual(indexed_count, 0)
        self.assertEqual(pipeline.skipped_doc_ids, ["S001"])
        pipeline.client.ensure_rollover_index.assert_not_called()
        pipeline.client.client.bulk.assert_not_called()

    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_fallback_doc_id_is_stable(
        self,
        _client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _standardizer_for,
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

    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_indexing_partial_bulk_errors_propagates_exception(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _standardizer_for,
    ):
        client = Mock()
        client.client.bulk.return_value = {
            "errors": True,
            "items": [{"index": {"status": 500, "error": {"type": "err"}}}],
        }
        client.ensure_rollover_index.return_value = "silver_scientific_production-000001"
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
        client.rollover.assert_not_called()

    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_indexing_generic_bulk_errors_propagates_exception(
        self,
        client_cls,
        _scielo_deduplicator_cls,
        _openalex_matcher_cls,
        _standardizer_for,
    ):
        client = Mock()
        client.client.bulk.side_effect = RuntimeError("cluster down")
        client.ensure_rollover_index.return_value = "silver_scientific_production-000001"
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
        client.rollover.assert_not_called()
