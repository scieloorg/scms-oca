from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from observation.views import (
    _build_dimension_table_result,
    _estimate_grand_total_journals,
)
from search_gateway.models import DataSource


class FakeObservationDataSource:
    field_settings = {
        "sdg": {
            "kind": "index",
            "index_field_name": "sdg_names",
            "settings": {"support_query_operator": True},
        },
        "country": {
            "kind": "index",
            "index_field_name": "author_country_codes",
            "settings": {"support_query_operator": True},
        },
        "publication_year": {
            "kind": "index",
            "index_field_name": "publication_year",
            "filter": {"size": 300},
        },
    }

    @property
    def field_settings_dict(self):
        return self.field_settings

    def get_field_settings_dict(self, include_fields=None, exclude_fields=None):
        return self.field_settings

    def get_ordered_fields(self, form_key=None):
        return []

    def get_form_field_names(self, form_key=None):
        return ["sdg", "country", "publication_year"]

    def get_search_field_mapping(self):
        return {"all": ["search_all_text"]}


class ObservationBooleanOperatorsTests(SimpleTestCase):
    @patch(
        "observation.views._apply_lookup_labels_to_rows",
        side_effect=lambda service, field, result, **kwargs: result,
    )
    @patch("observation.views._estimate_dimension_row_total", return_value=1)
    def test_dimension_table_preserves_boolean_operators(self, _mock_total, _mock_labels):
        data_source = DataSource(
            index_name="scientific_production",
            field_settings={
                "fields": FakeObservationDataSource.field_settings,
                "forms": {
                    "search": {
                        "fields": ["sdg", "country", "publication_year"],
                    }
                },
            },
        )
        service = Mock()
        service.data_source = data_source
        service.search_aggregation.return_value = {
            "columns": ["2024"],
            "rows": [{"key": "BR", "label": "BR", "values": {"2024": 1}}],
            "grand_total": 1,
        }
        query_source = RequestFactory().get(
            "/observation/table/?sdg=1&sdg=2&sdg_operator=and"
        ).GET

        _build_dimension_table_result(
            query_source,
            service,
            {
                "row_field_name": "country",
                "col_field_name": "publication_year",
            },
        )

        applied_filters = service.search_aggregation.call_args.kwargs["filters"]
        self.assertEqual(applied_filters["sdg"], ["1", "2"])
        self.assertEqual(applied_filters["sdg_operator"], "and")

    def test_estimate_grand_total_journals_passes_boolean_filters(self):
        client = Mock()
        client.search.return_value = {
            "aggregations": {"grand_total_journals": {"value": 42}}
        }
        service = Mock()
        service.client = client
        service.index_name = "scientific_production"
        service.request_timeout = 30
        service.field_settings = FakeObservationDataSource.field_settings

        filters = {
            "sdg": ["1. No Poverty", "2. Zero Hunger"],
            "sdg_operator": "and",
            "country": ["Brazil"],
            "country_bool_not": "true",
        }

        total = _estimate_grand_total_journals(
            service,
            query_text="",
            query_clauses=[],
            applied_filters=filters,
            journal_field="journal_id",
        )

        self.assertEqual(total, 42)
        body = client.search.call_args.kwargs["body"]
        bool_query = body["query"]["bool"]
        self.assertEqual(
            bool_query["filter"],
            [
                {"term": {"sdg_names": "1. No Poverty"}},
                {"term": {"sdg_names": "2. Zero Hunger"}},
            ],
        )
        self.assertEqual(
            bool_query["must_not"],
            [{"terms": {"author_country_codes": ["Brazil"]}}],
        )
