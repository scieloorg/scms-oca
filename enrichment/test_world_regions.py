from django.test import TestCase

from enrichment.models import WorldRegionsUpload
from enrichment.world_regions import world_regions_update_body


class WorldRegionsOpenSearchTests(TestCase):
    def setUp(self):
        self.upload = WorldRegionsUpload.objects.create(
            file="world_regions/regions.csv",
            mapping={"BR": "South America", "JP": "Eastern Asia"},
            active=True,
        )

    def test_update_body_uses_uploaded_mapping_and_document_ids(self):
        body = world_regions_update_body(
            self.upload.mapping,
            ["silver-1", "silver-2"],
        )

        self.assertEqual(
            body["query"]["bool"]["filter"],
            [{"ids": {"values": ["silver-1", "silver-2"]}}],
        )
        self.assertEqual(
            body["script"]["params"]["mapping"],
            self.upload.mapping,
        )

    def test_update_body_uses_all_mapping_by_default(self):
        body = world_regions_update_body(
            self.upload.mapping,
        )

        self.assertEqual(
            body["query"]["bool"]["should"][0]["terms"]["oca_data.scielo.source.country_code"],
            sorted(self.upload.mapping.keys()),
        )
