from django.test import SimpleTestCase

from indicator.metrics.config import MetricGroup
from indicator.metrics.query import MetricQuery


class FakeIndicatorDataSource:
    metric_config_schema = {
        "query": {
            "must": [{"term": {"status": "published"}}],
            "must_not": [],
        }
    }

    field_settings = {
        "sdg": {
            "kind": "index",
            "index_field_name": "sdg_names",
            "settings": {"support_query_operator": True},
        },
    }

    def get_field_settings_dict(self):
        return self.field_settings

    def get_index_field_name(self, field_name):
        return self.field_settings.get(field_name, {}).get("index_field_name", field_name)


class MetricQueryBooleanTests(SimpleTestCase):
    def setUp(self):
        self.data_source = FakeIndicatorDataSource()
        self.metric_group = MetricGroup("_filter", {}, [])

    def test_metric_query_with_and_operator_builds_separate_term_must_clauses(self):
        query_builder = MetricQuery(self.data_source, self.metric_group)
        filters = {
            "sdg": ["1. No Poverty", "2. Zero Hunger"],
            "sdg_operator": "and",
        }

        query = query_builder.build_query(filters)
        must = query["bool"]["must"]

        self.assertIn({"term": {"status": "published"}}, must)
        self.assertIn({"term": {"sdg_names": "1. No Poverty"}}, must)
        self.assertIn({"term": {"sdg_names": "2. Zero Hunger"}}, must)
