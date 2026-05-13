from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from etl.client import OpenSearchClient


class OpenSearchClientTests(SimpleTestCase):
    @patch("etl.client.get_opensearch_client")
    def test_index_exists_returns_true_when_index_present(self, get_client):
        mock_client = Mock()
        mock_client.indices.exists.return_value = True
        get_client.return_value = mock_client

        client = OpenSearchClient()
        self.assertTrue(client.index_exists("test_index"))

    @patch("etl.client.get_opensearch_client")
    def test_index_exists_returns_false_when_index_absent(self, get_client):
        mock_client = Mock()
        mock_client.indices.exists.return_value = False
        get_client.return_value = mock_client

        client = OpenSearchClient()
        self.assertFalse(client.index_exists("test_index"))

    @patch("etl.client.get_opensearch_client")
    def test_create_index_sends_correct_body(self, get_client):
        mock_client = Mock()
        mock_client.indices.exists.side_effect = [False, True]
        get_client.return_value = mock_client

        client = OpenSearchClient()
        mapping = {"mappings": {"properties": {"field": {"type": "keyword"}}}}
        client.create_index("test_index", mapping)

        mock_client.indices.create.assert_called_once_with(
            index="test_index",
            body=mapping,
        )
        mock_client.cluster.health.assert_called_once_with(
            index="test_index",
            wait_for_status="yellow",
            timeout=60,
        )

    @patch("etl.client.get_opensearch_client")
    def test_create_index_skips_if_already_exists(self, get_client):
        mock_client = Mock()
        mock_client.indices.exists.return_value = True
        get_client.return_value = mock_client

        client = OpenSearchClient()
        client.create_index("test_index", {})

        mock_client.indices.create.assert_not_called()

    @patch("etl.client.get_opensearch_client")
    def test_add_alias_puts_alias_on_index(self, get_client):
        mock_client = Mock()
        get_client.return_value = mock_client

        client = OpenSearchClient()
        client.add_alias("test_index", "my_alias")

        mock_client.indices.put_alias.assert_called_once_with(
            index="test_index",
            name="my_alias",
        )

    @patch("etl.client.get_opensearch_client")
    def test_accepts_url_parameter(self, get_client):
        get_client.return_value = Mock()
        client = OpenSearchClient(url="http://opensearch:9200")
        get_client.assert_called_once_with(
            url="http://opensearch:9200",
            host=None,
            port=None,
            use_ssl=False,
        )
        self.assertIsNotNone(client)
