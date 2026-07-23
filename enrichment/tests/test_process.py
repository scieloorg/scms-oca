from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from enrichment.exceptions import WorldRegionsProcessingError
from enrichment.models import WorldRegionsUpload
from enrichment.process import run_world_regions_upload
from search_gateway.models import DataSource


class WorldRegionsProcessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="processor")
        self.data_source = DataSource.objects.create(
            index_name="silver_scientific_production",
        )

    def create_upload(self):
        return WorldRegionsUpload.objects.create(
            creator=self.user,
            target_data_source=self.data_source,
            file="enrichment/regions.csv",
            mapping={"BR": "South America"},
            active=True,
        )

    @patch("enrichment.process.wait_for_task")
    @patch("enrichment.process.apply_world_regions")
    @patch("enrichment.process.concrete_indices")
    def test_run_persists_stats_for_each_index(
        self,
        concrete_indices,
        apply_world_regions,
        wait_for_task,
    ):
        upload = self.create_upload()
        concrete_indices.return_value = ["silver-000001", "silver-000002"]
        apply_world_regions.side_effect = ["node:1", "node:2"]
        wait_for_task.side_effect = [
            {"total": 10, "updated": 8, "noops": 2, "took": 100},
            {"total": 5, "updated": 1, "noops": 4, "took": 50},
        ]

        stats = run_world_regions_upload(upload.pk)

        upload.refresh_from_db()
        self.assertEqual(
            upload.status,
            WorldRegionsUpload.WorldRegionsStatus.APPLIED,
        )
        concrete_indices.assert_called_once_with(self.data_source.index_name)
        self.assertEqual(stats["total"], 15)
        self.assertEqual(stats["updated"], 9)
        self.assertEqual(stats["noops"], 6)
        self.assertEqual(len(stats["indices"]), 2)

    @patch("enrichment.process.wait_for_task")
    @patch("enrichment.process.apply_world_regions")
    @patch("enrichment.process.concrete_indices")
    def test_run_marks_upload_failed_on_version_conflict(
        self,
        concrete_indices,
        apply_world_regions,
        wait_for_task,
    ):
        upload = self.create_upload()
        concrete_indices.return_value = ["silver-000001"]
        apply_world_regions.return_value = "node:1"
        wait_for_task.return_value = {
            "total": 10,
            "updated": 9,
            "version_conflicts": 1,
        }

        with self.assertRaises(WorldRegionsProcessingError):
            run_world_regions_upload(upload.pk)

        upload.refresh_from_db()
        self.assertEqual(
            upload.status,
            WorldRegionsUpload.WorldRegionsStatus.FAILED,
        )
        self.assertEqual(upload.stats["version_conflicts"], 1)
