from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from enrichment.models import WorldRegionsUpload


class WorldRegionsWagtailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(self.user)

    @patch("enrichment.views.apply_world_regions_upload.delay")
    def test_apply_activates_upload_and_enqueues_task(self, delay):
        delay.return_value.id = "celery-1"
        old_upload = WorldRegionsUpload.objects.create(
            file="world_regions/old.csv",
            mapping={"AR": "South America"},
            active=True,
        )
        upload = WorldRegionsUpload.objects.create(
            file="world_regions/new.csv",
            mapping={"BR": "South America"},
        )

        response = self.client.get(
            reverse("enrichment_apply_world_regions", args=[upload.pk])
        )

        old_upload.refresh_from_db()
        upload.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(old_upload.active)
        self.assertTrue(upload.active)
        self.assertEqual(upload.task_id, "celery-1")
        delay.assert_called_once_with(upload.pk)

    def test_results_screen_shows_stats(self):
        upload = WorldRegionsUpload.objects.create(
            file="world_regions/regions.csv",
            mapping={"BR": "South America"},
            stats={"total": 10, "updated": 8, "noops": 2, "indices": []},
        )

        response = self.client.get(
            reverse("enrichment_world_regions_results", args=[upload.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10")
        self.assertContains(response, "8")
