from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from etl.models import EtlItemProcess, EtlPipelineConfig, EtlResult, EtlStatus


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

    def test_get_summary_stats_includes_match_counts(self):
        EtlItemProcess.objects.create(
            source_index="si",
            external_id="S1",
            document_type="article",
            status=EtlStatus.SUCCESS,
            result=EtlResult.MERGED,
            has_openalex_match=True,
        )
        EtlItemProcess.objects.create(
            source_index="si",
            external_id="S2",
            document_type="article",
            status=EtlStatus.SUCCESS,
            result=EtlResult.UPDATED,
            has_scielo_dedup=True,
        )

        stats = EtlItemProcess.objects.get_summary_stats()

        self.assertEqual(stats["status_counts"].get(EtlStatus.SUCCESS, 0), 2)
        self.assertEqual(stats["type_counts"].get("article", 0), 2)
        self.assertEqual(stats["openalex_counts"].get("article", 0), 1)
        self.assertEqual(stats["scielo_dedup_counts"].get("article", 0), 1)

    def test_get_summary_stats_includes_type_status_counts(self):
        EtlItemProcess.objects.create(
            source_index="si",
            external_id="P1",
            document_type="preprint",
            status=EtlStatus.PENDING,
        )

        stats = EtlItemProcess.objects.get_summary_stats()

        self.assertEqual(stats["type_status_counts"].get(("preprint", EtlStatus.PENDING), 0), 1)

    def test_pipeline_config_to_rules_with_empty_rules_json(self):
        config = EtlPipelineConfig(
            name="test",
            input_index="test_index",
            silver_index_pattern="silver_test",
            input_document_kind="article",
            default_document_type="article",
            rules={},
        )
        rules = config.to_rules()

        self.assertEqual(rules["document_type"], "article")
        self.assertEqual(rules["scielo_dedup_strategies"], [])
        self.assertEqual(rules["openalex_match_strategies"], [])
        self.assertEqual(rules["doi_requires_title_overlap"], True)
        self.assertEqual(rules["fuzzy_min_similarity"], 0.85)
        self.assertEqual(rules["openalex_validation"]["min_score"], 50)

    def test_pipeline_config_to_rules_with_partial_rules_json(self):
        config = EtlPipelineConfig(
            name="partial",
            input_index="partial_index",
            silver_index_pattern="silver_partial",
            input_document_kind="article",
            default_document_type="article",
            rules={
                "scielo_dedup_strategies": ["doi"],
                "fuzzy_min_similarity": 0.90,
                "openalex_validation": {"min_score": 70},
            },
        )
        rules = config.to_rules()

        self.assertEqual(rules["scielo_dedup_strategies"], ["doi"])
        self.assertEqual(rules["fuzzy_min_similarity"], 0.90)
        self.assertEqual(rules["openalex_validation"]["min_score"], 70)
        self.assertEqual(rules["doi_requires_title_overlap"], True)
