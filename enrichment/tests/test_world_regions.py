from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from enrichment.exceptions import WorldRegionsProcessingError
from enrichment.models import WorldRegionsUpload
from enrichment.world_regions import (
    apply_world_regions,
    apply_world_regions_to_documents,
    world_regions_update_body,
)
from search_gateway.models import DataSource


class WorldRegionsOpenSearchTests(SimpleTestCase):
    def setUp(self):
        self.mapping = {"BR": "South America", "JP": "Eastern Asia"}

    def test_update_body_uses_uploaded_mapping_and_document_ids(self):
        body = world_regions_update_body(
            self.mapping,
            ["doc1", "doc2"],
        )

        self.assertEqual(
            body["query"]["bool"]["filter"],
            [{"ids": {"values": ["doc1", "doc2"]}}],
        )
        self.assertEqual(
            body["script"]["params"]["mapping"],
            self.mapping,
        )

    @patch("enrichment.world_regions.get_opensearch_client")
    def test_apply_requires_task_id(self, get_client):
        get_client.return_value.update_by_query.return_value = {}

        with self.assertRaises(WorldRegionsProcessingError):
            apply_world_regions("silver-000001", self.mapping)


class IncrementalWorldRegionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="processor")
        self.data_source = DataSource.objects.create(
            index_name="silver_scientific_production",
        )
        other_data_source = DataSource.objects.create(index_name="other_index")
        self.upload = WorldRegionsUpload.objects.create(
            creator=self.user,
            target_data_source=self.data_source,
            file="enrichment/regions.csv",
            mapping={"BR": "South America"},
            active=True,
        )
        WorldRegionsUpload.objects.create(
            creator=self.user,
            target_data_source=other_data_source,
            file="enrichment/other.csv",
            mapping={"JP": "Eastern Asia"},
            active=True,
        )

    @patch("enrichment.world_regions.wait_for_task")
    @patch("enrichment.world_regions.apply_world_regions")
    @patch("enrichment.world_regions.concrete_indices")
    def test_incremental_application_uses_target_upload_and_waits_for_task(
        self,
        concrete_indices,
        apply_regions,
        wait_for_task,
    ):
        concrete_indices.return_value = ["silver-000001"]
        apply_regions.return_value = "node:1"
        wait_for_task.return_value = {"total": 1, "updated": 1}

        results = apply_world_regions_to_documents(
            ["doc1"],
            self.data_source.index_name,
        )

        apply_regions.assert_called_once()
        self.assertEqual(
            apply_regions.call_args.args,
            ("silver-000001", self.upload.mapping),
        )
        self.assertEqual(
            apply_regions.call_args.kwargs["document_ids"],
            ["doc1"],
        )
        wait_for_task.assert_called_once_with("node:1", 5)
        self.assertEqual(
            results,
            [{"index": "silver-000001", "total": 1, "updated": 1}],
        )
