from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from enrichment.models import WorldRegionsUpload


class WorldRegionsUploadTests(TestCase):
    def test_upload_normalizes_world_regions(self):
        upload = WorldRegionsUpload(
            file=SimpleUploadedFile(
                "regions.csv",
                b"country_code;world_region\nbr;South America\njp;Eastern Asia\n",
            )
        )

        upload.full_clean()

        self.assertEqual(
            upload.mapping,
            {"BR": "South America", "JP": "Eastern Asia"},
        )

    def test_upload_rejects_duplicate_country_codes(self):
        upload = WorldRegionsUpload(
            file=SimpleUploadedFile(
                "regions.csv",
                b"country_code;world_region\nBR;South America\nbr;Other\n",
            )
        )

        with self.assertRaises(ValidationError):
            upload.full_clean()
