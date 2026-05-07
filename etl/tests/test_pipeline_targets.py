from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from etl.pipeline.defaults import resolve_target_names
from etl.tasks import _run_pipeline_target


class PipelineTargetTests(SimpleTestCase):
    def test_resolve_all_targets(self):
        self.assertEqual(
            resolve_target_names("all"),
            ["article"],
        )

    @override_settings(
        OS_URL="http://opensearch:9200",
        OP_INDEX_SCIENTIFIC_PRODUCTION="silver_*",
        ETL_PUBLIC_ALIAS="scientific_production",
    )
    @patch("etl.tasks.OpenSearchETLPipeline")
    def test_run_pipeline_target_builds_django_configured_pipeline(self, pipeline_cls):
        pipeline_cls.return_value.run.return_value = {"errors": 0, "total_indexed_docs": 2}
        pipeline_cls.return_value.indexed_index_names = {"silver_article_2024"}

        result = _run_pipeline_target("article", year=2024, max_docs=10)

        pipeline_cls.assert_called_once()
        kwargs = pipeline_cls.call_args.kwargs
        self.assertEqual(kwargs["opensearch_url"], "http://opensearch:9200")
        self.assertEqual(kwargs["bronze_scielo_index"], "bronze_scielo_articles-000001")
        self.assertEqual(kwargs["silver_index_pattern"], "silver_article_{year}")
        self.assertEqual(kwargs["public_alias"], "scientific_production")
        self.assertEqual(result["target"], "article")
        self.assertEqual(result["indexed_indices"], ["silver_article_2024"])
