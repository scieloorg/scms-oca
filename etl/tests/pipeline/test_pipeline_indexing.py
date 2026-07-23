from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

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
        self.assertEqual(pipeline.indexed_document_ids, ["S001"])
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
    def test_indexing_defers_world_regions_until_after_global_metrics(
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
        pipeline = OpenSearchETLPipeline(opensearch_url="http://opensearch:9200")
        doc = SilverDocument(
            doc_id="S001",
            type="article",
            publication_year=2024,
            author_country_codes=["BR", "JP"],
            oca_data={
                "scielo": {"source": {"country_code": "BR"}},
                "openalex": {},
            },
        )

        pipeline._index_silver_documents([doc])

        indexed_document = client.client.bulk.call_args.kwargs["body"][1]
        self.assertNotIn(
            "world_region",
            indexed_document["oca_data"]["scielo"]["source"],
        )
        self.assertNotIn("openalex", indexed_document["oca_data"])

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

    @override_settings(ETL_SILVER_BULK_MAX_DOCS=2, ETL_SILVER_BULK_MAX_BYTES=1024 * 1024)
    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_indexing_splits_bulk_requests_by_configured_document_count(
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
            SilverDocument(doc_id=f"S00{i}", type="article", publication_year=2024, title=f"Title {i}")
            for i in range(5)
        ]

        indexed_count = pipeline._index_silver_documents(docs)

        self.assertEqual(indexed_count, 5)
        self.assertEqual(client.client.bulk.call_count, 3)
        chunk_lengths = [
            len(call.kwargs["body"])
            for call in client.client.bulk.call_args_list
        ]
        self.assertEqual(chunk_lengths, [4, 4, 2])
        client.rollover.assert_called_once()

    @patch("etl.pipeline.standardizer_for")
    @patch("etl.pipeline.OpenAlexMatcher")
    @patch("etl.pipeline.SciELODeduplicator")
    @patch("etl.pipeline.OpenSearchClient")
    def test_indexing_duplicate_doc_id_with_conflicting_content_uses_alternate_id(
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
        scl_doc = SilverDocument(
            doc_id="S0034-71672025000400101",
            type="article",
            publication_year=2025,
            title="In-person nursing education",
            doi="10.1590/0034-7167.2025780402",
            openalex_id="https://openalex.org/W1",
        )
        rve_doc = SilverDocument(
            doc_id="S0034-71672025000400101",
            type="article",
            publication_year=2025,
            title="Ethical dilemmas in nursing professionals' work",
            doi="10.1590/0034-7167.202578supl101",
            ids={"openalex": ["https://openalex.org/W2", "https://openalex.org/W3"]},
            openalex_id="https://openalex.org/W2",
        )

        with self.assertLogs("etl.pipeline", level="WARNING") as logs:
            indexed_count = pipeline._index_silver_documents([scl_doc, rve_doc])

        self.assertEqual(indexed_count, 2)
        self.assertIn("Conflicting silver documents share doc_id", "\n".join(logs.output))
        bulk_body = client.client.bulk.call_args.kwargs["body"]
        self.assertEqual(bulk_body[0]["index"]["_id"], "S0034-71672025000400101")
        self.assertEqual(bulk_body[1]["title"], "Ethical dilemmas in nursing professionals' work")
        self.assertTrue(bulk_body[2]["index"]["_id"].startswith("S0034-71672025000400101__"))
        self.assertNotEqual(bulk_body[0]["index"]["_id"], bulk_body[2]["index"]["_id"])

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
