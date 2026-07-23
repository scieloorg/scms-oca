import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from enrichment.models import WorldRegionsUpload
from search_gateway.models import DataSource


class WorldRegionsUploadTests(TestCase):
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

    def test_upload_normalizes_world_regions(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("wagtailsnippets_enrichment_worldregionsupload:add"),
                    {
                        "target_data_source": self.data_source.pk,
                        "file": SimpleUploadedFile(
                            "regions.csv",
                            b"country_code;world_region\n"
                            b"br;South America\n"
                            b"jp;Eastern Asia\n",
                            content_type="text/csv",
                        ),
                    },
                )

        upload = WorldRegionsUpload.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            upload.mapping,
            {"BR": "South America", "JP": "Eastern Asia"},
        )
        self.assertEqual(upload.creator, self.user)

    def test_upload_rejects_duplicate_country_codes(self):
        response = self.client.post(
            reverse("wagtailsnippets_enrichment_worldregionsupload:add"),
            {
                "target_data_source": self.data_source.pk,
                "file": SimpleUploadedFile(
                    "regions.csv",
                    b"country_code;world_region\nBR;South America\nbr;Other\n",
                    content_type="text/csv",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Código de país duplicado")
        self.assertFalse(WorldRegionsUpload.objects.exists())
