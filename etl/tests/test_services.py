from unittest.mock import patch

from django.test import TestCase, override_settings

from etl.models import EtlItemProcess, EtlResult, EtlStatus
from etl.services import enqueue_etl_item, process_pending_items, source_hash


class EtlServiceTests(TestCase):
    def test_source_hash_ignores_indexing_metadata(self):
        self.assertEqual(
            source_hash({"raw_data": {"a": 1}}),
            source_hash({"a": 1, "oca_indexed_at": "now", "oca_source_hash": "old"}),
        )

    def test_enqueue_creates_pending_item(self):
        item = enqueue_etl_item(
            source_index="bronze_scielo_articles",
            external_id="S1",
            source_payload={"publication_year": 2024, "title": "A"},
            document_type="article",
        )

        self.assertEqual(item.status, EtlStatus.PENDING)
        self.assertEqual(item.document_type, "article")
        self.assertEqual(item.publication_year, 2024)

    def test_enqueue_reopens_success_item_when_hash_changes(self):
        item = enqueue_etl_item(
            source_index="bronze_scielo_articles",
            external_id="S1",
            source_payload={"publication_year": 2024, "title": "A"},
            document_type="article",
        )
        item.mark_success(EtlResult.UPDATED)

        changed = enqueue_etl_item(
            source_index="bronze_scielo_articles",
            external_id="S1",
            source_payload={"publication_year": 2024, "title": "B"},
            document_type="article",
        )

        self.assertEqual(changed.status, EtlStatus.PENDING)
        self.assertEqual(changed.result, "")
        self.assertIsNone(changed.processed_at)
        self.assertEqual(EtlItemProcess.objects.count(), 1)

    @override_settings(ETL_ERROR_INDEX="etl_errors")
    @patch("etl.services.log_etl_error")
    @patch("etl.services.SilverETLPipeline")
    def test_process_pending_marks_success(self, pipeline_cls, _log_etl_error):
        item = enqueue_etl_item(
            source_index="bronze_scielo_articles",
            external_id="S1",
            source_payload={"publication_year": 2024, "title": "A"},
            document_type="article",
        )
        pipeline_cls.return_value.run.return_value = {
            "errors": 0,
            "total_indexed_docs": 1,
        }
        pipeline_cls.return_value.indexed_index_names = {"silver_article_2024"}
        pipeline_cls.return_value.loaded_source_ids = {"S1"}

        result = process_pending_items(
            source_index="bronze_scielo_articles",
            document_type="article",
            silver_index_pattern="silver_article_{year}",
            limit=10,
        )

        item.refresh_from_db()
        self.assertEqual(item.status, EtlStatus.SUCCESS)
        self.assertEqual(item.result, EtlResult.UPDATED)
        self.assertEqual(result[0]["indexed_indices"], ["silver_article_2024"])
        pipeline_cls.return_value.run.assert_called_once_with(
            year_filter=2024,
            doc_ids=["S1"],
        )

    @override_settings(ETL_ERROR_INDEX="etl_errors")
    @patch("etl.services.log_etl_error")
    @patch("etl.services.SilverETLPipeline")
    def test_process_pending_marks_failed(self, pipeline_cls, log_etl_error):
        item = enqueue_etl_item(
            source_index="bronze_scielo_articles",
            external_id="S1",
            source_payload={"publication_year": 2024, "title": "A"},
            document_type="article",
        )
        pipeline_cls.return_value.run.side_effect = RuntimeError("boom")

        result = process_pending_items(
            source_index="bronze_scielo_articles",
            document_type="article",
            silver_index_pattern="silver_article_{year}",
            limit=10,
        )

        item.refresh_from_db()
        self.assertEqual(item.status, EtlStatus.FAILED)
        self.assertEqual(item.result, EtlResult.ERROR)
        self.assertIn("boom", item.error)
        self.assertEqual(result[0]["errors"], 1)
        log_etl_error.assert_called_once()
