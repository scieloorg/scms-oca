from django.test import SimpleTestCase

from etl.transform.extractors import (
    extract_abstract_from_inverted_index,
    extract_display_name,
    extract_doi,
    extract_identifiers,
    extract_isbns,
    extract_issns,
    extract_scielo_id,
    extract_source,
    extract_titles,
)


class IdentifierExtractorTests(SimpleTestCase):
    def test_extract_doi_reads_top_level_ids_and_language_items(self):
        self.assertEqual(extract_doi({"doi": "10.1590/a"}), "10.1590/a")
        self.assertEqual(extract_doi({"ids": {"doi": "10.1590/b"}}), "10.1590/b")
        self.assertEqual(
            extract_doi({"doi_with_lang": [{"language": "pt", "doi": "10.1590/c"}]}),
            "10.1590/c",
        )

    def test_extract_isbns_reads_document_parent_and_location_values(self):
        doc = {
            "isbn": "978-65-00-00000-1",
            "parent_book": {"ids": {"isbn": "85-359-0277-5"}},
            "primary_location": {"source": {"issns": ["9788500000002"]}},
        }

        self.assertEqual(
            extract_isbns(doc),
            ["8535902775", "9786500000001", "9788500000002"],
        )

    def test_extract_issns_normalizes_source_values(self):
        doc = {
            "source_issns": ["0102-311X"],
            "source": {"issn": "0034-8910"},
            "primary_location": {"source": {"issns": ["1415-790X"]}},
        }

        self.assertEqual(extract_issns(doc), ["0034-8910", "0102-311X", "1415-790X"])

    def test_extract_scielo_id_prefers_explicit_values(self):
        self.assertEqual(extract_scielo_id({"scielo_id": "S1"}), "S1")
        self.assertEqual(extract_scielo_id({"pid_v2": "S2"}), "S2")
        self.assertEqual(extract_scielo_id({"ids": {"scl_preprint_id": "P1"}}), "P1")

    def test_extract_identifiers_builds_indexed_identifier_shape(self):
        identifiers = extract_identifiers(
            {
                "doi": "https://doi.org/10.1590/S0102-311X2024000100001",
                "issn": ["bad", "0102-311X"],
                "isbn": "978-65-00-00000-1",
                "pid_v2": "S1",
                "pmid": 123,
            }
        )

        self.assertEqual(identifiers["doi"], "10.1590/s0102-311x2024000100001")
        self.assertEqual(identifiers["issn"], "0102-311X")
        self.assertEqual(identifiers["isbn"], "9786500000001")
        self.assertNotIn("openalex_id", identifiers)
        self.assertEqual(identifiers["scielo_id"], "S1")
        self.assertEqual(identifiers["pmid"], "123")


class SourceAndTextExtractorTests(SimpleTestCase):
    def test_extract_source_prefers_top_level_source(self):
        self.assertEqual(
            extract_source({"source": {"title": "Journal"}}),
            {"title": "Journal"},
        )

    def test_extract_source_falls_back_to_location_source(self):
        self.assertEqual(
            extract_source({"primary_location": {"source": {"title": "Book"}}}),
            {"title": "Book"},
        )

    def test_extract_titles_reads_multilingual_titles_first(self):
        titles = extract_titles(
            {
                "title": "Fallback title",
                "title_with_lang": [{"language": "pt", "title": "T\u00edtulo"}],
            }
        )

        self.assertEqual(titles, ["titulo"])

    def test_extract_titles_falls_back_to_display_name(self):
        self.assertEqual(
            extract_titles({"display_name": "OpenAlex title"}),
            ["openalex title"],
        )

    def test_extract_abstract_from_inverted_index_orders_tokens(self):
        abstract = extract_abstract_from_inverted_index(
            {"world": [1], "Hello": [0], "again": [2]}
        )

        self.assertEqual(abstract, "Hello world again")

    def test_extract_display_name_reads_common_name_fields(self):
        self.assertEqual(extract_display_name({"display_name": "Name"}), "Name")
        self.assertEqual(extract_display_name("raw"), "raw")
