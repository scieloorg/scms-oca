from django.test import SimpleTestCase

from etl.schema import SILVER_MAPPING, SILVER_PROPERTIES


class SilverMappingTests(SimpleTestCase):
    def test_silver_mapping_is_strict(self):
        self.assertEqual(SILVER_MAPPING["mappings"]["dynamic"], "strict")

    def test_silver_mapping_contains_contract_fields(self):
        for field in ("doc_id", "type", "ids", "oca_data", "metrics"):
            self.assertIn(field, SILVER_PROPERTIES)

    def test_scope_is_keyword(self):
        self.assertEqual(
            SILVER_PROPERTIES["oca_data"]["properties"]["scope"],
            {"type": "keyword"},
        )
