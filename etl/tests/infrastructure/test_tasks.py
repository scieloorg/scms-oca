from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase

from etl.tasks import process_pending_silver_etl, retry_failed_silver_etl, run_silver_etl


class CommandAndTaskTests(SimpleTestCase):
    @patch("etl.management.commands.run_silver_etl.run_pipeline_targets")
    def test_run_silver_etl_command_calls_runner(self, run_pipeline_targets):
        run_pipeline_targets.return_value = [
            {"target": "article", "errors": 0, "total_indexed_docs": 1}
        ]
        out = StringIO()

        call_command(
            "run_silver_etl",
            "--type",
            "article",
            "--year",
            "2024",
            "--max-docs",
            "10",
            stdout=out,
        )

        run_pipeline_targets.assert_called_once_with(
            "article",
            year=2024,
            max_docs=10,
            openalex_index="raw_openalex_works",
        )
        self.assertIn('"total_indexed_docs": 1', out.getvalue())

    @patch("etl.tasks.run_pipeline_targets")
    def test_run_silver_etl_task_calls_runner(self, run_pipeline_targets):
        run_pipeline_targets.return_value = [{"target": "article", "errors": 0}]

        result = run_silver_etl(
            target_type="article",
            year=2024,
            max_docs=10,
        )

        run_pipeline_targets.assert_called_once_with(
            "article",
            year=2024,
            max_docs=10,
            openalex_index="raw_openalex_works",
        )
        self.assertEqual(result, [{"target": "article", "errors": 0}])

    @patch("etl.management.commands.run_silver_etl.process_pending_items")
    def test_run_silver_etl_command_processes_pending(self, process_pending_items):
        process_pending_items.return_value = [{"errors": 0, "item_count": 1}]
        out = StringIO()

        call_command("run_silver_etl", "--pending", "--limit", "5", stdout=out)

        process_pending_items.assert_called_once_with(limit=5, retry_failed=False)
        self.assertIn('"item_count": 1', out.getvalue())

    @patch("etl.tasks.process_pending_items")
    def test_pending_tasks_call_service(self, process_pending_items):
        process_pending_items.return_value = [{"errors": 0}]

        self.assertEqual(process_pending_silver_etl(limit=2), [{"errors": 0}])
        process_pending_items.assert_called_with(limit=2, document_type=None)

        self.assertEqual(retry_failed_silver_etl(limit=3), [{"errors": 0}])
        process_pending_items.assert_called_with(limit=3, retry_failed=True)
