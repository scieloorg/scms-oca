from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from etl.tasks import process_pending_silver_etl, retry_failed_silver_etl, run_silver_etl


class SilverEtlTaskTests(SimpleTestCase):
    @override_settings(OS_URL="http://opensearch:9200", ETL_DEFAULT_BATCH_SIZE=1000)
    @patch("etl.tasks.SilverETLPipeline")
    def test_run_task_executes_pipeline(self, pipeline_cls):
        pipeline_cls.return_value.run.return_value = {"errors": 0, "total_indexed_docs": 1}
        pipeline_cls.return_value.indexed_index_names = {"silver_article_2024"}

        result = run_silver_etl(
            source_index="bronze_scielo_articles",
            document_type="article",
            silver_index_pattern="silver_article_{year}",
            year=2024,
            max_docs=10,
        )

        pipeline_cls.return_value.run.assert_called_once_with(
            max_docs=10,
            year_filter=2024,
        )
        self.assertEqual(result["indexed_indices"], ["silver_article_2024"])

    @override_settings(ETL_DEFAULT_BATCH_SIZE=1000)
    @patch("etl.tasks.process_pending_items")
    def test_pending_and_retry_tasks_call_service(self, process_pending_items):
        process_pending_items.return_value = [{"errors": 0}]

        self.assertEqual(
            process_pending_silver_etl(
                source_index="bronze_scielo_articles",
                document_type="article",
                silver_index_pattern="silver_article_{year}",
                limit=2,
            ),
            [{"errors": 0}],
        )
        process_pending_items.assert_called_with(
            source_index="bronze_scielo_articles",
            document_type="article",
            silver_index_pattern="silver_article_{year}",
            limit=2,
        )

        self.assertEqual(
            retry_failed_silver_etl(
                source_index="bronze_scielo_articles",
                document_type="article",
                silver_index_pattern="silver_article_{year}",
                limit=3,
            ),
            [{"errors": 0}],
        )
        process_pending_items.assert_called_with(
            source_index="bronze_scielo_articles",
            document_type="article",
            silver_index_pattern="silver_article_{year}",
            limit=3,
            retry_failed=True,
        )
