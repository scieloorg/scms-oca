from django.test import SimpleTestCase

from etl.indexing.schema import SILVER_MAPPING, SILVER_PROPERTIES
from etl.documents import BronzeDocument, SilverDocument
from etl.transform.standardizer import DefaultStandardizer


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


class StandardizerPipelineTests(SimpleTestCase):
    def test_step_errors_are_not_silently_ignored(self):
        pipeline = DefaultStandardizer()

        def failing_step(data, _bronze):
            raise RuntimeError("bad source payload")

        pipeline.steps = [failing_step]

        with self.assertRaisesRegex(RuntimeError, "bad source payload"):
            pipeline.run(BronzeDocument(doc_id="S001", document_type="article"))
