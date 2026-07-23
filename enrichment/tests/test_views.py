from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from enrichment.models import WorldRegionsUpload
from search_gateway.models import DataSource


class WorldRegionsWagtailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(self.user)
        self.data_source = DataSource.objects.create(
            index_name="silver_scientific_production",
        )
        self.other_data_source = DataSource.objects.create(
            index_name="other_index",
        )

    @patch("enrichment.views.apply_world_regions_upload.delay")
    def test_apply_activates_upload_and_enqueues_task(self, delay):
        delay.return_value.id = "celery-1"
        old_upload = WorldRegionsUpload.objects.create(
            creator=self.user,
            target_data_source=self.data_source,
            file="enrichment/old.csv",
            mapping={"AR": "South America"},
            active=True,
        )
        other_upload = WorldRegionsUpload.objects.create(
            creator=self.user,
            target_data_source=self.other_data_source,
            file="enrichment/other.csv",
            mapping={"JP": "Eastern Asia"},
            active=True,
        )
        upload = WorldRegionsUpload.objects.create(
            creator=self.user,
            target_data_source=self.data_source,
            file="enrichment/new.csv",
            mapping={"BR": "South America"},
        )

        response = self.client.get(
            reverse("enrichment_apply_world_regions", args=[upload.pk])
        )

        old_upload.refresh_from_db()
        other_upload.refresh_from_db()
        upload.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(old_upload.active)
        self.assertTrue(other_upload.active)
        self.assertTrue(upload.active)
        self.assertRedirects(
            response,
            reverse("wagtailsnippets_enrichment_worldregionsupload:list"),
        )
        delay.assert_called_once_with(upload.pk)

    def test_results_screen_shows_stats(self):
        upload = WorldRegionsUpload.objects.create(
            creator=self.user,
            target_data_source=self.data_source,
            file="enrichment/regions.csv",
            mapping={"BR": "South America"},
            stats={"total": 10, "updated": 8, "noops": 2, "indices": []},
        )

        response = self.client.get(
            reverse("enrichment_world_regions_results", args=[upload.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10")
        self.assertContains(response, "8")
