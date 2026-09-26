from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from harvest.mappings.bronze_preprint import BRONZE_MAPPING as PREPRINT_MAPPING


class CreateBronzeIndicesTests(SimpleTestCase):
    @patch("harvest.management.commands.create_bronze_indices.get_opensearch_client")
    def test_creates_custom_index_with_selected_mapping(self, get_client):
        client = MagicMock()
        client.indices.exists.return_value = False
        get_client.return_value = client

        call_command("create_bronze_indices", index="preprint", name="bronze_scl_preprint")

        client.indices.exists.assert_called_once_with(index="bronze_scl_preprint")
        client.indices.create.assert_called_once_with(
            index="bronze_scl_preprint", body=PREPRINT_MAPPING
        )

    @patch("harvest.management.commands.create_bronze_indices.get_opensearch_client")
    def test_name_requires_index(self, get_client):
        get_client.return_value = MagicMock()

        with self.assertRaisesMessage(CommandError, "--name requer --index"):
            call_command("create_bronze_indices", name="bronze_scl_preprint")

        get_client.return_value.indices.create.assert_not_called()
