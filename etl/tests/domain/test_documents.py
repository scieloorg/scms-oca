from django.test import SimpleTestCase

from etl.documents import (
    BronzeInputDocument,
    RawOpenAlexInputDocument,
    SilverDocument,
    SciELOArticleInputDocument,
    SciELODatasetInputDocument,
    SciELOPreprintInputDocument,
)


class BronzeDocumentContractTests(SimpleTestCase):
    def test_bronze_input_document_is_abstract(self):
        with self.assertRaises(TypeError):
            BronzeInputDocument(doc_id="S1", raw_data={"type": "article"})

    def test_input_document_requires_doc_id(self):
        with self.assertRaises(ValueError):
            SciELOArticleInputDocument(
                doc_id="",
                raw_data={"code": "", "type": "article"},
            )

    def test_input_document_validates_publication_year(self):
        with self.assertRaises(ValueError):
            SciELOArticleInputDocument(
                doc_id="S1",
                raw_data={"type": "article"},
                publication_year=999,
            )

    def test_bronze_from_raw_extracts_fields(self):
        def doc_type_fn(raw):
            return "article"

        bronze = SciELOArticleInputDocument.from_raw(
            {"code": "S123", "type": "research-article", "publication_year": 2024},
            doc_type_fn=doc_type_fn,
        )
        self.assertEqual(bronze.doc_id, "S123")
        self.assertEqual(bronze.document_type, "article")
        self.assertEqual(bronze.publication_year, 2024)
        self.assertEqual(bronze.scope, ["scielo"])

    def test_bronze_from_raw_fallback_doc_id(self):
        def doc_type_fn(raw):
            return "preprint"

        def fallback_fn(raw):
            return "doc_fallback123"

        bronze = SciELOPreprintInputDocument.from_raw(
            {"publication_year": 2024},
            doc_type_fn=doc_type_fn,
            fallback_id_fn=fallback_fn,
        )
        self.assertEqual(bronze.doc_id, "doc_fallback123")

    def test_direct_scielo_input_defaults_document_type(self):
        self.assertEqual(SciELOArticleInputDocument(doc_id="A1").document_type, "article")
        self.assertEqual(SciELOPreprintInputDocument(doc_id="P1").document_type, "preprint")
        self.assertEqual(SciELODatasetInputDocument(doc_id="D1").document_type, "dataset")

    def test_openalex_from_raw_extracts_fields(self):
        oa = RawOpenAlexInputDocument.from_raw(
            {
                "id": "https://openalex.org/W1",
                "type": "article",
                "publication_year": 2024,
                "doi": "https://doi.org/10.1590/S0102-311X2024000100001",
            }
        )
        self.assertEqual(oa.doc_id, "https://openalex.org/W1")
        self.assertEqual(oa.document_type, "article")
        self.assertEqual(oa.publication_year, 2024)
        self.assertEqual(oa.scope, ["openalex"])


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
