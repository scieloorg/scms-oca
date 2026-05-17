from django.test import SimpleTestCase

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
            doi="10.1590/s0102-311x2024000100001",
            ids={"openalex_with_lang": [{"language": "en", "openalex": "W999"}]},
            openalex_id="https://openalex.org/W999",
            scielo_id="S001",
            oca_data={"scope": "scielo"},
        )

        indexed = doc.to_index_dict()

        self.assertEqual(indexed["doc_id"], "S001")
        self.assertNotIn("doi", indexed)
        self.assertEqual(indexed["ids"]["doi"], "10.1590/s0102-311x2024000100001")
        self.assertEqual(indexed["ids"]["openalex"], "https://openalex.org/W999")
        self.assertEqual(
            indexed["ids"]["openalex_with_lang"],
            [{"language": "en", "openalex": "https://openalex.org/W999"}],
        )
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

    def test_silver_document_indexes_sdg_names_flat(self):
        doc = SilverDocument(
            doc_id="S001",
            type="article",
            sustainable_development_goals=[
                {"id": "1", "display_name": "No poverty", "score": 0.9},
                {"id": "1", "display_name": "No poverty", "score": 0.8},
                {"id": "2", "display_name": "Zero hunger", "score": 0.7},
            ],
        )

        indexed = doc.to_index_dict()

        self.assertEqual(indexed["sdg_names"], ["No poverty", "Zero hunger"])
