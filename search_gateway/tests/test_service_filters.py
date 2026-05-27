from unittest.mock import Mock

from django.test import SimpleTestCase

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
