from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from etl.models import EtlItemProcess, EtlResult, EtlStatus


class EtlItemProcessModelTests(TestCase):
    def test_mark_processing_increments_attempts(self):
        item = EtlItemProcess.objects.create(
            source_index="bronze_scielo_articles",
            external_id="S1",
            document_type="article",
        )

        item.mark_processing()

        self.assertEqual(item.status, EtlStatus.PROCESSING)
        self.assertEqual(item.attempts, 1)

    def test_mark_success_records_result_and_processed_at(self):
        item = EtlItemProcess.objects.create(
            source_index="bronze_scielo_articles",
            external_id="S1",
            document_type="article",
        )

        item.mark_success(EtlResult.CREATED)

        self.assertEqual(item.status, EtlStatus.SUCCESS)
        self.assertEqual(item.result, EtlResult.CREATED)
        self.assertIsNotNone(item.processed_at)

    def test_mark_failed_records_truncated_error(self):
        item = EtlItemProcess.objects.create(
            source_index="bronze_scielo_articles",
            external_id="S1",
            document_type="article",
        )

        item.mark_failed("x" * 6000)

        self.assertEqual(item.status, EtlStatus.FAILED)
        self.assertEqual(item.result, EtlResult.ERROR)
        self.assertEqual(len(item.error), 5000)

    def test_requeue_stale_processing_marks_items_pending(self):
        item = EtlItemProcess.objects.create(
            source_index="bronze_scielo_articles",
            external_id="S1",
            document_type="article",
            status=EtlStatus.PROCESSING,
        )
        EtlItemProcess.objects.filter(pk=item.pk).update(
            updated_at=timezone.now() - timedelta(minutes=31)
        )

        updated = EtlItemProcess.objects.requeue_stale_processing()

        item.refresh_from_db()
        self.assertEqual(updated, 1)
        self.assertEqual(item.status, EtlStatus.PENDING)
