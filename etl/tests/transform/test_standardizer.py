from django.test import SimpleTestCase

from etl.documents import (
    RawOpenAlexInputDocument,
    SciELOArticleInputDocument,
    SciELOBookInputDocument,
)
from etl.transform.standardizer import standardizer_for, SciELOStandardizer, OpenAlexStandardizer


class SciELOStandardizerTests(SimpleTestCase):
    def test_standardizes_basic_source_payload(self):
        def doc_type_fn(raw):
            return "article"

        bronze = SciELOArticleInputDocument.from_raw(
            {
                "code": "S1",
                "type": "article",
                "title": "  Sa\u00fade coletiva  ",
                "abstract": "Resumo",
                "doi": "https://doi.org/10.1590/S0102-311X2024000100001",
                "publication_year": "2024",
                "language": "por",
                "journal_title": "Journal",
                "country_code": "bra",
                "cited_by_count": 3,
            },
            doc_type_fn=doc_type_fn,
        )

        silver = SciELOStandardizer().run(bronze)

        self.assertEqual(silver.doc_id, "S1")
        self.assertEqual(silver.type, "article")
        self.assertEqual(silver.title, "Saude coletiva")
        self.assertEqual(silver.doi, "10.1590/s0102-311x2024000100001")
        self.assertEqual(silver.publication_year, 2024)
        self.assertEqual(silver.language, ["pt"])
        self.assertEqual(silver.source["title"], "Journal")
        self.assertEqual(silver.metrics["received_citations"]["total"], 3)
        self.assertEqual(silver.oca_data["scope"], ["scielo"])

    def test_standardizer_for_dispatches_correctly(self):
        def doc_type_fn(raw):
            return "article"

        bronze = SciELOArticleInputDocument.from_raw(
            {"code": "S1", "type": "article", "publication_year": 2024},
            doc_type_fn=doc_type_fn,
        )
        std = standardizer_for(bronze)
        self.assertIsInstance(std, SciELOStandardizer)

        oa = RawOpenAlexInputDocument.from_raw(
            {"id": "https://openalex.org/W1", "type": "article"}
        )
        std = standardizer_for(oa)
        self.assertIsInstance(std, OpenAlexStandardizer)

    def test_standardizes_canonical_document_type_from_alias(self):
        def doc_type_fn(raw):
            return raw["type"]

        bronze = SciELOArticleInputDocument.from_raw(
            {"code": "S1", "type": "research-article", "publication_year": 2024},
            doc_type_fn=doc_type_fn,
        )

        silver = standardizer_for(bronze).run(bronze)

        self.assertEqual(silver.type, "article")
        self.assertEqual(silver.oca_data["scielo"]["type"], "research-article")

    def test_standardizes_satellite_document_type_from_alias(self):
        def doc_type_fn(raw):
            return raw["type"]

        bronze = SciELOArticleInputDocument.from_raw(
            {"code": "S1", "type": "erratum", "publication_year": 2024},
            doc_type_fn=doc_type_fn,
        )

        silver = standardizer_for(bronze).run(bronze)

        self.assertEqual(silver.type, "correction")
        self.assertEqual(silver.oca_data["scielo"]["type"], "erratum")


class OpenAlexStandardizerTests(SimpleTestCase):
    def test_rebuilds_openalex_abstract_from_inverted_index(self):
        oa = RawOpenAlexInputDocument.from_raw(
            {
                "id": "https://openalex.org/W1",
                "type": "article",
                "display_name": "OpenAlex work",
                "abstract_inverted_index": {"hello": [0], "world": [1]},
            }
        )

        silver = OpenAlexStandardizer().run(oa)

        self.assertEqual(silver.title, "OpenAlex work")
        self.assertEqual(silver.abstract, "hello world")
        self.assertEqual(silver.oca_data["scope"], ["openalex"])


class StandardizerIdentifierTests(SimpleTestCase):
    def test_top_level_identifiers_are_populated_from_scielo(self):
        def doc_type_fn(raw):
            return "article"

        bronze = SciELOArticleInputDocument.from_raw(
            {
                "code": "S123",
                "type": "article",
                "doi": "https://doi.org/10.1590/S0102-311X2024000100001",
                "publication_year": 2024,
                "language": "pt",
                "openalex_with_lang": [
                    {"language": "pt", "openalex": "65def291ba8c91985ed38f97"},
                    {"language": "en", "openalex": "W123"},
                ],
            },
            doc_type_fn=doc_type_fn,
        )

        silver = SciELOStandardizer().run(bronze)
        self.assertEqual(silver.doi, "10.1590/s0102-311x2024000100001")
        self.assertEqual(silver.scielo_id, "S123")
        self.assertEqual(silver.ids["doi"], "10.1590/s0102-311x2024000100001")
        self.assertEqual(
            silver.ids["doi_with_lang"],
            [{"language": "pt", "doi": "10.1590/s0102-311x2024000100001"}],
        )
        self.assertEqual(silver.ids["scielo"], "S123")
        self.assertNotIn("openalex_with_lang", silver.ids)

    def test_top_level_identifiers_are_populated_from_openalex(self):
        oa = RawOpenAlexInputDocument.from_raw(
            {
                "id": "W1",
                "type": "article",
                "doi": "https://doi.org/10.1590/S0102-311X2024000100001",
                "publication_year": 2024,
                "language": "en",
            }
        )

        silver = standardizer_for(oa).run(oa)
        self.assertEqual(silver.doi, "10.1590/s0102-311x2024000100001")
        self.assertEqual(silver.openalex_id, "https://openalex.org/W1")
        self.assertEqual(silver.ids["doi"], "10.1590/s0102-311x2024000100001")
        self.assertEqual(silver.ids["openalex"], "https://openalex.org/W1")
        self.assertEqual(
            silver.ids["openalex_with_lang"],
            [{"language": "en", "openalex": "https://openalex.org/W1"}],
        )

    def test_standardizer_error_propagates_not_silently_ignored(self):
        def doc_type_fn(raw):
            return "article"

        bronze = SciELOArticleInputDocument.from_raw(
            {"code": "S001", "type": "article", "publication_year": 2024},
            doc_type_fn=doc_type_fn,
        )

        class FailingStandardizer(SciELOStandardizer):
            def _build_document_fields(self, input_doc):
                raise RuntimeError("bad source payload")

        with self.assertRaisesRegex(RuntimeError, "bad source payload"):
            FailingStandardizer().run(bronze)

    def test_pipeline_creates_book_input_for_book_target(self):
        def doc_type_fn(raw):
            return raw.get("type", "book")

        book = SciELOBookInputDocument.from_raw(
            {"id": "B1", "type": "book", "publication_year": 2024},
            doc_type_fn=doc_type_fn,
        )
        silver = standardizer_for(book).run(book)
        self.assertIn("scielo", silver.oca_data.get("scope", []))
