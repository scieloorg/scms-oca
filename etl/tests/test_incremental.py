from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from etl.models import EtlItemProcess, EtlResult, EtlStatus
from etl.services import enqueue_etl_item, process_pending_items
from harvest.utils import source_hash


class IncrementalEtlTests(TestCase):
    def test_source_hash_is_deterministic_and_uses_raw_data(self):
        self.assertEqual(
            source_hash({"b": 2, "a": 1}),
            source_hash({"a": 1, "b": 2}),
        )
        self.assertEqual(
            source_hash({"raw_data": {"a": 1}}),
            source_hash({"a": 1}),
        )
        self.assertEqual(
            source_hash({"a": 1, "oca_indexed_at": "now", "oca_source_hash": "old"}),
            source_hash({"a": 1}),
        )

    def test_enqueue_creates_pending_item(self):
        item = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p1",
            source_payload={"publication_year": 2024, "title": "A"},
        )

        self.assertEqual(item.status, EtlStatus.PENDING)
        self.assertEqual(item.document_type, "book")
        self.assertEqual(item.publication_year, 2024)
        self.assertEqual(EtlItemProcess.objects.count(), 1)

    def test_enqueue_reopens_success_item_when_hash_changes(self):
        item = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p1",
            source_payload={"publication_year": 2024, "title": "A"},
        )
        item.mark_success(EtlResult.UPDATED)

        changed = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p1",
            source_payload={"publication_year": 2024, "title": "B"},
        )

        self.assertEqual(changed.status, EtlStatus.PENDING)
        self.assertEqual(changed.result, "")
        self.assertIsNone(changed.processed_at)
        self.assertEqual(EtlItemProcess.objects.count(), 1)

    @patch("etl.services.log_etl_error")
    @patch("etl.services.OpenSearchETLPipeline")
    def test_process_pending_marks_success(self, pipeline_cls, _log_etl_error):
        item = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p1",
            source_payload={"publication_year": 2024, "title": "A"},
        )
        pipeline_cls.return_value.run.return_value = {
            "errors": 0,
            "total_indexed_docs": 1,
            "groups_with_openalex_matches": 0,
            "total_duplicates_found": 0,
        }
        pipeline_cls.return_value.indexed_index_names = {"silver_book_2024"}
        pipeline_cls.return_value.loaded_source_ids = {"p1"}

        result = process_pending_items(limit=10)

        item.refresh_from_db()
        self.assertEqual(item.status, EtlStatus.SUCCESS)
        self.assertEqual(item.result, EtlResult.UPDATED)
        self.assertEqual(result[0]["indexed_indices"], ["silver_book_2024"])
        pipeline_cls.return_value.run.assert_called_once_with(
            year_filter=2024,
            doc_ids=["p1"],
        )

    @patch("etl.services.log_etl_error")
    @patch("etl.services.OpenSearchETLPipeline")
    def test_process_pending_marks_failed(self, pipeline_cls, log_etl_error):
        item = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p1",
            source_payload={"publication_year": 2024, "title": "A"},
        )
        pipeline_cls.return_value.run.side_effect = RuntimeError("boom")

        result = process_pending_items(limit=10)

        item.refresh_from_db()
        self.assertEqual(item.status, EtlStatus.FAILED)
        self.assertEqual(item.result, EtlResult.ERROR)
        self.assertIn("boom", item.error)
        self.assertEqual(result[0]["errors"], 1)
        log_etl_error.assert_called_once()

    @patch("etl.services.log_etl_error")
    @patch("etl.services.OpenSearchETLPipeline")
    def test_process_pending_fails_when_pipeline_indexes_nothing(
        self,
        pipeline_cls,
        log_etl_error,
    ):
        item = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="missing",
            source_payload={"publication_year": 2024, "title": "A"},
        )
        pipeline_cls.return_value.run.return_value = {
            "errors": 0,
            "total_indexed_docs": 0,
            "groups_with_openalex_matches": 0,
            "total_duplicates_found": 0,
        }
        pipeline_cls.return_value.indexed_index_names = set()
        pipeline_cls.return_value.loaded_source_ids = {"missing"}

        result = process_pending_items(limit=10)

        item.refresh_from_db()
        self.assertEqual(item.status, EtlStatus.FAILED)
        self.assertIn("did not index", item.error)
        self.assertEqual(result[0]["errors"], 1)
        log_etl_error.assert_called_once()

    @patch("etl.services.log_etl_error")
    @patch("etl.services.OpenSearchETLPipeline")
    def test_process_pending_requeues_stale_processing_items(
        self,
        pipeline_cls,
        _log_etl_error,
    ):
        item = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p-stale",
            source_payload={"publication_year": 2024, "title": "A"},
        )
        item.status = EtlStatus.PROCESSING
        item.save(update_fields=["status", "updated_at"])
        EtlItemProcess.objects.filter(pk=item.pk).update(
            updated_at=timezone.now() - timedelta(minutes=31)
        )

        pipeline_cls.return_value.run.return_value = {
            "errors": 0,
            "total_indexed_docs": 1,
            "groups_with_openalex_matches": 0,
            "total_duplicates_found": 0,
        }
        pipeline_cls.return_value.indexed_index_names = {"silver_book_2024"}
        pipeline_cls.return_value.loaded_source_ids = {"p-stale"}

        result = process_pending_items(limit=10)

        item.refresh_from_db()
        self.assertEqual(item.status, EtlStatus.SUCCESS)
        self.assertEqual(result[0]["item_count"], 1)

    @patch("etl.services.log_etl_error")
    @patch("etl.services.OpenSearchETLPipeline")
    def test_process_pending_fails_group_when_requested_source_id_is_missing(
        self,
        pipeline_cls,
        log_etl_error,
    ):
        item_1 = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p1",
            source_payload={"publication_year": 2024, "title": "A"},
        )
        item_2 = enqueue_etl_item(
            source_index="bronze_scielo_books",
            external_id="p2",
            source_payload={"publication_year": 2024, "title": "B"},
        )
        pipeline_cls.return_value.run.return_value = {
            "errors": 0,
            "total_indexed_docs": 1,
            "groups_with_openalex_matches": 0,
            "total_duplicates_found": 0,
        }
        pipeline_cls.return_value.indexed_index_names = {"silver_book_2024"}
        pipeline_cls.return_value.loaded_source_ids = {"p1"}

        result = process_pending_items(limit=10)

        item_1.refresh_from_db()
        item_2.refresh_from_db()
        self.assertEqual(item_1.status, EtlStatus.FAILED)
        self.assertEqual(item_2.status, EtlStatus.FAILED)
        self.assertIn("p2", item_1.error)
        self.assertEqual(result[0]["errors"], 2)
        self.assertEqual(log_etl_error.call_count, 2)
