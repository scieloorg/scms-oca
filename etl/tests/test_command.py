from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class RunSilverEtlCommandTests(SimpleTestCase):
    @override_settings(OS_URL="http://opensearch:9200")
    @patch("etl.management.commands.run_silver_etl.SilverETLPipeline")
    def test_command_runs_pipeline_with_explicit_target(self, pipeline_cls):
        pipeline_cls.return_value.run.return_value = {"errors": 0, "total_indexed_docs": 1}
        pipeline_cls.return_value.indexed_index_names = {"silver_article_2024"}
        out = StringIO()

        call_command(
            "run_silver_etl",
            "--source-index",
            "bronze_scielo_articles",
            "--document-type",
            "article",
            "--silver-index",
            "silver_article_{year}",
            "--year",
            "2024",
            "--max-docs",
            "10",
            stdout=out,
        )

        pipeline_cls.return_value.run.assert_called_once_with(
            max_docs=10,
            year_filter=2024,
        )
        self.assertIn('"total_indexed_docs": 1', out.getvalue())

    @patch("etl.management.commands.run_silver_etl.process_pending_items")
    def test_command_processes_pending_items(self, process_pending_items):
        process_pending_items.return_value = [{"errors": 0, "item_count": 1}]
        out = StringIO()

        call_command(
            "run_silver_etl",
            "--source-index",
            "bronze_scielo_articles",
            "--document-type",
            "article",
            "--silver-index",
            "silver_article_{year}",
            "--pending",
            "--limit",
            "5",
            stdout=out,
        )

        process_pending_items.assert_called_once_with(
            source_index="bronze_scielo_articles",
            document_type="article",
            silver_index_pattern="silver_article_{year}",
            limit=5,
            retry_failed=False,
        )
        self.assertIn('"item_count": 1', out.getvalue())
