from django.test import SimpleTestCase

from etl.indexing.contracts import BronzeDocument, SilverDocument


class BronzeDocumentContractTests(SimpleTestCase):
    def test_bronze_document_requires_doc_id(self):
        with self.assertRaisesRegex(ValueError, "doc_id"):
            BronzeDocument(doc_id="", document_type="article", source="scielo")

    def test_bronze_document_validates_publication_year(self):
        with self.assertRaisesRegex(ValueError, "publication_year"):
            BronzeDocument(
                doc_id="S1",
                document_type="article",
                source="scielo",
                publication_year=999,
            )


class SilverDocumentContractTests(SimpleTestCase):
    def test_silver_document_serializes_index_shape(self):
        doc = SilverDocument(
            doc_id="S1",
            type="article",
            publication_year=2024,
            title="Test title",
            doi="10.1590/test",
            scielo_id="S1",
            citation_count=2,
            oca_data={"scope": "scielo"},
        )

        indexed = doc.to_index_dict()

        self.assertEqual(indexed["doc_id"], "S1")
        self.assertEqual(indexed["type"], "article")
        self.assertEqual(indexed["ids"]["doi"], "10.1590/test")
        self.assertEqual(indexed["ids"]["scielo"], "S1")
        self.assertEqual(indexed["metrics"]["received_citations"]["total"], 2)
        self.assertEqual(indexed["oca_data"]["scope"], ["scielo"])

    def test_silver_document_detects_merged_scope(self):
        doc = SilverDocument(
            doc_id="S1",
            type="article",
            oca_data={"scope": ["scielo", "openalex"]},
        )

        self.assertTrue(doc.is_merged())
