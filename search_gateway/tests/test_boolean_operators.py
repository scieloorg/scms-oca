from unittest.mock import Mock

from django.test import SimpleTestCase

from search_gateway.models import DataSource
from search_gateway.query import build_filter_clauses
from search_gateway.service import SearchGatewayService


FIELD_SETTINGS = {
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
    "source_type": {
        "kind": "index",
        "index_field_name": "type",
        "settings": {"support_query_operator": False},
    },
}


class BooleanOperatorFilterTests(SimpleTestCase):
    def test_multi_value_with_and_operator_builds_separate_term_clauses(self):
        filters = {
            "sdg": ["1. No Poverty", "2. Zero Hunger"],
            "sdg_operator": "and",
        }

        filter_clauses, must_not_clauses = build_filter_clauses(
            filters,
            field_settings=FIELD_SETTINGS,
        )

        self.assertEqual(
            filter_clauses,
            [
                {"term": {"sdg_names": "1. No Poverty"}},
                {"term": {"sdg_names": "2. Zero Hunger"}},
            ],
        )
        self.assertEqual(must_not_clauses, [])

    def test_multi_value_with_or_operator_builds_single_terms_clause(self):
        filters = {
            "sdg": ["1. No Poverty", "2. Zero Hunger"],
            "sdg_operator": "or",
        }

        filter_clauses, must_not_clauses = build_filter_clauses(
            filters,
            field_settings=FIELD_SETTINGS,
        )

        self.assertEqual(
            filter_clauses,
            [{"terms": {"sdg_names": ["1. No Poverty", "2. Zero Hunger"]}}],
        )
        self.assertEqual(must_not_clauses, [])

    def test_multi_value_without_support_operator_always_uses_terms_clause(self):
        filters = {
            "source_type": ["journal", "book"],
            "source_type_operator": "and",
        }

        filter_clauses, must_not_clauses = build_filter_clauses(
            filters,
            field_settings=FIELD_SETTINGS,
        )

        self.assertEqual(
            filter_clauses,
            [{"terms": {"type": ["journal", "book"]}}],
        )
        self.assertEqual(must_not_clauses, [])

    def test_field_without_support_operator_ignores_bool_not(self):
        filters = {
            "source_type": "journal",
            "source_type_bool_not": "true",
        }

        filter_clauses, must_not_clauses = build_filter_clauses(
            filters,
            field_settings=FIELD_SETTINGS,
        )

        self.assertEqual(filter_clauses, [{"term": {"type": "journal"}}])
        self.assertEqual(must_not_clauses, [])

    def test_field_with_bool_not_active_routes_to_must_not(self):
        filters = {
            "country": ["Brazil"],
            "country_bool_not": "true",
        }

        filter_clauses, must_not_clauses = build_filter_clauses(
            filters,
            field_settings=FIELD_SETTINGS,
        )

        self.assertEqual(filter_clauses, [])
        self.assertEqual(
            must_not_clauses,
            [{"terms": {"author_country_codes": ["Brazil"]}}],
        )
