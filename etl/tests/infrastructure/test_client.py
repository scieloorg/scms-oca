from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from etl.client import OpenSearchClient


class OpenSearchClientTests(SimpleTestCase):
    @patch("etl.client.get_opensearch_client")
    def test_ensure_rollover_index_creates_bootstrap_with_aliases(self, get_client):
        mock_client = Mock()
        mock_client.indices.exists.side_effect = [False, True]
        get_client.return_value = mock_client

        client = OpenSearchClient()
        mapping = {"settings": {}, "mappings": {"properties": {}}}
        index_name = client.ensure_rollover_index(
            index_prefix="silver_scientific_production",
            write_alias="silver_write",
            public_alias="scientific_production",
            mapping=mapping,
        )

        self.assertEqual(index_name, "silver_scientific_production-000001")
        mock_client.indices.put_index_template.assert_called_once_with(
            name="silver_scientific_production_rollover_template",
            body={
                "index_patterns": ["silver_scientific_production-*"],
                "template": {
                    "settings": {},
                    "mappings": {"properties": {}},
                    "aliases": {"scientific_production": {}},
                },
            },
        )
        mock_client.indices.create.assert_called_once_with(
            index="silver_scientific_production-000001",
            body={
                "settings": {},
                "mappings": {"properties": {}},
                "aliases": {
                    "silver_write": {"is_write_index": True},
                    "scientific_production": {},
                },
            },
        )
        self.assertNotIn("aliases", mapping)

    @patch("etl.client.get_opensearch_client")
    def test_ensure_rollover_index_skips_when_write_alias_exists(self, get_client):
        mock_client = Mock()
        mock_client.indices.exists.return_value = True
        get_client.return_value = mock_client

        client = OpenSearchClient()
        index_name = client.ensure_rollover_index(
            index_prefix="silver_scientific_production",
            write_alias="silver_write",
            public_alias="scientific_production",
            mapping={},
        )

        self.assertIsNone(index_name)
        mock_client.indices.put_index_template.assert_called_once_with(
            name="silver_scientific_production_rollover_template",
            body={
                "index_patterns": ["silver_scientific_production-*"],
                "template": {"aliases": {"scientific_production": {}}},
            },
        )
        mock_client.indices.create.assert_not_called()

    @patch("etl.client.get_opensearch_client")
    def test_rollover_applies_mapping_and_adds_public_alias_to_new_index(self, get_client):
        mock_client = Mock()
        mock_client.indices.rollover.return_value = {
            "rolled_over": True,
            "new_index": "silver_scientific_production-000002",
        }
        get_client.return_value = mock_client

        client = OpenSearchClient()
        new_index = client.rollover(
            write_alias="silver_write",
            public_alias="scientific_production",
            mapping={"settings": {"number_of_shards": 1}, "mappings": {"dynamic": "strict"}},
            max_size="10gb",
        )

        self.assertEqual(new_index, "silver_scientific_production-000002")
        mock_client.indices.rollover.assert_called_once_with(
            alias="silver_write",
            body={
                "conditions": {"max_size": "10gb", "max_docs": 500},
                "settings": {"number_of_shards": 1},
                "mappings": {"dynamic": "strict"},
            },
        )
        mock_client.indices.put_alias.assert_called_once_with(
            index="silver_scientific_production-000002",
            name="scientific_production",
        )
