from unittest.mock import Mock

from django.test import SimpleTestCase
from django.utils.translation import override

from search_gateway.models import DataSource
from search_gateway.query import build_bool_from_clauses
from search_gateway.service import SearchGatewayService


class FakeDataSource:
    field_settings = {
        "document_type": {
            "kind": "index",
            "index_field_name": "type",
            "filter": {"size": 30},
        },
        "document_language": {
            "kind": "index",
            "index_field_name": "language",
            "filter": {"size": 500},
        },
    }

    def get_field_settings_dict(self, include_fields=None, exclude_fields=None):
        include_fields = set(include_fields or [])
        exclude_fields = set(exclude_fields or [])
        if not include_fields and not exclude_fields:
            return self.field_settings

        return {
            field_name: field_config
            for field_name, field_config in self.field_settings.items()
            if (not include_fields or field_name in include_fields)
            and field_name not in exclude_fields
        }


class FiltersDataTests(SimpleTestCase):
    def test_included_filter_options_are_restricted_by_other_fields(self):
        client = Mock()
        client.search.return_value = {
            "aggregations": {
                "document_language": {
                    "buckets": [],
                },
            },
        }
        service = SearchGatewayService(index_name="scientific_production", client=client)
        service.__dict__["data_source"] = FakeDataSource()

        filters, error = service.get_filters_data(
            include_fields=["document_language"],
            filters={"document_type": "retraction"},
        )

        self.assertIsNone(error)
        self.assertEqual(filters, {"document_language": []})
        body = client.search.call_args.kwargs["body"]
        self.assertEqual(body["aggs"], {"document_language": {"terms": {"field": "language", "size": 500}}})
        self.assertEqual(body["query"], {"bool": {"filter": [{"term": {"type": "retraction"}}]}})

    def test_search_kind_fields_are_not_used_as_filter_options(self):
        client = Mock()
        client.search.return_value = {
            "aggregations": {
                "document_language": {
                    "buckets": [],
                },
            },
        }
        service = SearchGatewayService(index_name="scientific_production", client=client)
        service.__dict__["data_source"] = FakeDataSource()
        service.data_source.field_settings = {
            **service.data_source.field_settings,
            "title_search": {
                "kind": "search",
                "index_field_name": "title_search",
                "filter": {"size": 10},
            },
        }

        _filters, error = service.get_filters_data()

        self.assertIsNone(error)
        body = client.search.call_args.kwargs["body"]
        self.assertNotIn("title_search", body["aggs"])


class SearchFieldConfigTests(SimpleTestCase):
    def test_datasource_builds_searchable_fields_from_search_kind_fields(self):
        data_source = DataSource(
            index_name="silver_scientific_production",
            field_settings={
                "fields": {
                    "document_type": {
                        "kind": "index",
                        "index_field_name": "type",
                    },
                    "all": {
                        "kind": "search",
                        "index_field_name": "search_all_text",
                        "settings": {
                            "label": "All fields",
                            "field_search_enabled": True,
                            "field_search_order": 0,
                        },
                    },
                    "keywords_search": {
                        "kind": "search",
                        "index_field_name": "keywords_search",
                        "settings": {
                            "label": "Keyword",
                            "field_search_enabled": True,
                            "field_search_order": 10,
                        },
                    },
                },
                "forms": {},
            },
        )

        with override("en"):
            self.assertEqual(
                data_source.get_searchable_fields(),
                [("all", "All fields"), ("keywords_search", "Keyword")],
            )

        self.assertEqual(
            data_source.get_search_field_mapping(),
            {
                "all": ["search_all_text"],
                "keywords_search": ["keywords_search"],
            },
        )

    def test_datasource_builds_all_from_search_fields_when_all_is_not_configured(self):
        data_source = DataSource(
            index_name="social_production",
            field_settings={
                "fields": {
                    "title_search": {
                        "kind": "search",
                        "index_field_name": "title_search",
                        "settings": {
                            "label": "Title",
                            "field_search_enabled": True,
                            "field_search_order": 10,
                        },
                    },
                    "text": {
                        "kind": "search",
                        "index_field_name": "text",
                        "settings": {
                            "label": "Text",
                            "field_search_enabled": True,
                            "field_search_order": 20,
                        },
                    },
                },
                "forms": {},
            },
        )

        with override("en"):
            self.assertEqual(
                data_source.get_searchable_fields(),
                [("all", "All fields"), ("title_search", "Title"), ("text", "Text")],
            )

        self.assertEqual(
            data_source.get_search_field_mapping(),
            {
                "title_search": ["title_search"],
                "text": ["text"],
                "all": ["title_search", "text"],
            },
        )

    def test_unknown_search_clause_uses_datasource_all_mapping(self):
        query = build_bool_from_clauses(
            [{"field": "legacy_field", "text": "open science"}],
            search_field_mapping={"all": ["search_all_text"]},
        )

        self.assertEqual(
            query,
            {
                "must": [
                    {
                        "multi_match": {
                            "query": "open science",
                            "fields": ["search_all_text"],
                            "operator": "and",
                        }
                    }
                ],
                "must_not": [],
            },
        )
