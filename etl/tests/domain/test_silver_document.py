from django.test import SimpleTestCase

from etl.mapping_silver import SILVER_MAPPING, SILVER_PROPERTIES
from etl.documents import SilverDocument


class SilverContractTests(SimpleTestCase):
    def test_silver_document_uses_index_contract_shape(self):
        doc = SilverDocument(
            doc_id="S001",
            type="article",
            publication_year=2024,
            title="Test title",
            abstract_with_lang=[{"lang": "pt", "text": "Resumo"}],
            description="A preprint description",
            description_with_lang=[{"language": "pt", "description": "Descrição"}],
            keywords_with_lang=[{"language": "pt", "keyword": ["a", "b"]}],
            subjects=["Chagas Disease", "Social Support"],
            subjects_with_lang=[{"language": "en", "subjects": "Chagas Disease"}],
            referenced_works=["https://openalex.org/W123"],
            openalex_id="https://openalex.org/W999",
            scielo_id="S001",
            oca_data={"scope": "scielo"},
        )

        indexed = doc.to_index_dict()

        self.assertEqual(indexed["doc_id"], "S001")
        self.assertEqual(indexed["ids"]["openalex"], "https://openalex.org/W999")
        self.assertEqual(indexed["ids"]["scielo"], "S001")
        self.assertEqual(indexed["oca_data"]["scope"], ["scielo"])
        self.assertEqual(indexed["description"], "A preprint description")
        self.assertEqual(
            indexed["description_with_lang"],
            [{"language": "pt", "description": "Descrição"}],
        )
        self.assertEqual(
            indexed["abstract_with_lang"],
            [{"language": "pt", "abstract": "Resumo"}],
        )
        self.assertEqual(
            indexed["keywords_with_lang"],
            [{"language": "pt", "keywords": ["a", "b"]}],
        )
        self.assertEqual(indexed["subjects"], ["Chagas Disease", "Social Support"])
        self.assertEqual(
            indexed["subjects_with_lang"],
            [{"language": "en", "subjects": "Chagas Disease"}],
        )
        self.assertEqual(
            indexed["referenced_works"],
            {"ids": {"openalex": ["https://openalex.org/W123"]}},
        )
        self.assertTrue(set(indexed).issubset(SILVER_PROPERTIES))

    def test_silver_mapping_is_strict_and_contains_expected_fields(self):
        self.assertEqual(SILVER_MAPPING["mappings"]["dynamic"], "strict")
        self.assertEqual(
            SILVER_PROPERTIES["oca_data"]["properties"]["scope"],
            {"type": "keyword"},
        )
        self.assertIn("ids", SILVER_PROPERTIES)
        self.assertIn("source", SILVER_PROPERTIES)
        self.assertIn("topic", SILVER_PROPERTIES)
        self.assertIn("metrics", SILVER_PROPERTIES)

    def test_silver_mapping_search_autocomplete_fields(self):
        self.assertEqual(SILVER_PROPERTIES["title_search_autocomplete"]["type"], "search_as_you_type")
        self.assertEqual(SILVER_PROPERTIES["abstract_search_autocomplete"]["type"], "search_as_you_type")
        self.assertEqual(SILVER_PROPERTIES["authors_search_autocomplete"]["type"], "search_as_you_type")
        self.assertEqual(SILVER_PROPERTIES["institutions_search_autocomplete"]["type"], "search_as_you_type")

    def test_silver_mapping_copy_to_aggregated_search_fields(self):
        self.assertEqual(
            SILVER_PROPERTIES["title"]["copy_to"],
            ["title_search", "title_search_autocomplete", "search_all_text"],
        )
        self.assertEqual(
            SILVER_PROPERTIES["abstract"]["copy_to"],
            ["abstract_search", "abstract_search_autocomplete", "search_all_text"],
        )
        self.assertEqual(
            SILVER_PROPERTIES["authorships"]["properties"]["name"]["copy_to"],
            ["authors_search", "authors_search_autocomplete", "search_all_text"],
        )
        self.assertEqual(
            SILVER_PROPERTIES["authorships"]["properties"]["institutions"]["properties"]["name"]["copy_to"],
            ["institutions_search", "institutions_search_autocomplete", "search_all_text"],
        )

    def test_silver_mapping_contains_contract_fields(self):
        for field in ("doc_id", "type", "ids", "oca_data", "metrics"):
            self.assertIn(field, SILVER_PROPERTIES)

    def test_scope_is_keyword(self):
        self.assertEqual(
            SILVER_PROPERTIES["oca_data"]["properties"]["scope"],
            {"type": "keyword"},
        )
