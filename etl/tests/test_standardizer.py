from django.test import SimpleTestCase

from etl.documents import InputDocument
from etl.transform.standardizer import DefaultStandardizer


class DefaultStandardizerTests(SimpleTestCase):
    def test_standardizes_basic_source_payload(self):
        bronze = InputDocument(
            doc_id="S1",
            document_type="article",
            source="scielo",
            raw_data={
                "title": "  Sa\u00fade coletiva  ",
                "abstract": "Resumo",
                "doi": "https://doi.org/10.1590/S0102-311X2024000100001",
                "publication_year": "2024",
                "language": "por",
                "journal_title": "Journal",
                "country_code": "bra",
                "cited_by_count": 3,
            },
        )

        silver = DefaultStandardizer().run(bronze)

        self.assertEqual(silver.doc_id, "S1")
        self.assertEqual(silver.type, "article")
        self.assertEqual(silver.title, "Saude coletiva")
        self.assertEqual(silver.doi, "10.1590/s0102-311x2024000100001")
        self.assertEqual(silver.publication_year, 2024)
        self.assertEqual(silver.language, ["pt"])
        self.assertEqual(silver.source["title"], "Journal")
        self.assertEqual(silver.metrics["received_citations"]["total"], 3)
        self.assertEqual(silver.oca_data["scope"], ["scielo"])

    def test_rebuilds_openalex_abstract_from_inverted_index(self):
        bronze = InputDocument(
            doc_id="https://openalex.org/W1",
            document_type="article",
            source="openalex",
            raw_data={
                "display_name": "OpenAlex work",
                "abstract_inverted_index": {"hello": [0], "world": [1]},
            },
        )

        silver = DefaultStandardizer().run(bronze)

        self.assertEqual(silver.title, "OpenAlex work")
        self.assertEqual(silver.abstract, "hello world")
        self.assertEqual(silver.oca_data["scope"], ["openalex"])
