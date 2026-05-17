from unittest.mock import patch

from django.test import TestCase, override_settings

from etl.models import EtlItemProcess, EtlResult, EtlStatus
from etl.tasks import _run_pipeline_target


class PipelineConfigTaskTests(TestCase):
    @override_settings(
        OS_URL="http://opensearch:9200",
        OP_INDEX_SCIENTIFIC_PRODUCTION="silver_*",
        ETL_PUBLIC_ALIAS="scientific_production",
    )
    @patch("etl.tasks.backfill_input_items")
    @patch("etl.tasks.refresh_db_connections")
    @patch("etl.tasks.OpenSearchETLPipeline")
    def test_run_pipeline_target_builds_django_configured_pipeline(
        self,
        pipeline_cls,
        refresh_db_connections,
        backfill_input_items,
    ):
        EtlItemProcess.objects.create(
            source_index="bronze_scielo_articles*",
            external_id="p1",
            document_type="article",
            publication_year=2024,
            source_hash="hash",
            status=EtlStatus.SUCCESS,
            result=EtlResult.UNCHANGED,
        )
        pipeline_cls.return_value.run.return_value = {"errors": 0, "total_indexed_docs": 2}
        pipeline_cls.return_value.public_alias = "scientific_production"
        pipeline_cls.return_value.indexed_index_names = {"silver"}

        result = _run_pipeline_target("article", year=2024, max_docs=10)

        pipeline_cls.assert_called_once()
        kwargs = pipeline_cls.call_args.kwargs
        self.assertEqual(kwargs["opensearch_url"], "http://opensearch:9200")
        self.assertEqual(kwargs["input_scielo_index"], "bronze_scielo_articles*")
        self.assertEqual(kwargs["public_alias"], "scientific_production")
        backfill_input_items.assert_called_once_with(
            "bronze_scielo_articles*",
            year=2024,
            limit=10,
            initial_status="success",
        )
        self.assertEqual(result["target"], "article")
        self.assertEqual(result["public_alias"], "scientific_production")
        self.assertEqual(result["indexed_indices"], ["silver"])
        self.assertGreaterEqual(refresh_db_connections.call_count, 4)
