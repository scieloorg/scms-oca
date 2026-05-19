from django.test import SimpleTestCase

from etl.documents import SilverDocument
from etl.transform.merger import SilverMerger


class MergeTests(SimpleTestCase):
    def test_merge_keeps_primary_doc_fields_and_records_trace(self):
        primary = SilverDocument(
            doc_id="S1",
            type="article",
            title="SciELO title",
            oca_data={"scope": ["scielo"]},
        )
        enrichment = SilverDocument(
            doc_id="https://openalex.org/W1",
            type="article",
            title="OpenAlex title",
            doi="10.1590/openalex",
            ids={"doi_with_lang": [{"language": "en", "doi": "10.1590/openalex"}]},
            openalex_id="https://openalex.org/W1",
            oca_data={"scope": ["openalex"]},
        )

        merged = SilverMerger().merge(
            scielo_docs=[primary],
            openalex_matches=[(enrichment, "doi", "high", {})],
        )

        self.assertEqual(merged.title, "SciELO title")
        self.assertEqual(merged.doi, "10.1590/openalex")
        self.assertEqual(merged.ids["doi"], "10.1590/openalex")
        self.assertEqual(
            merged.ids["doi_with_lang"],
            [{"language": "en", "doi": "10.1590/openalex"}],
        )
        self.assertEqual(merged.oca_data["scope"], ["scielo", "openalex"])
        self.assertEqual(merged.oca_data["merge_trace"]["openalex_matches"][0]["match_strategy"], "doi")

    def test_merge_handles_book_chapter_without_rules(self):
        primary = SilverDocument(
            doc_id="C1",
            type="book-chapter",
            title="Chapter title",
            publication_year=2024,
            oca_data={"scope": ["scielo"]},
        )

        merged = SilverMerger().merge(
            scielo_docs=[primary],
            openalex_matches=[],
        )

        self.assertEqual(merged.type, "book-chapter")
        self.assertEqual(merged.oca_data["scope"], ["scielo"])

    def test_merge_consolidates_multiple_scielo_duplicates(self):
        doc_a = SilverDocument(
            doc_id="A1",
            type="article",
            title="Same Article",
            scielo_id="A1",
            oca_data={"scope": ["scielo"], "scielo": {"collection": "scl", "pid_v2": "A1"}},
        )
        doc_b = SilverDocument(
            doc_id="A2",
            type="article",
            title="Same Article",
            scielo_id="A2",
            oca_data={"scope": ["scielo"], "scielo": {"collection": "col", "pid_v2": "A2"}},
        )

        merged = SilverMerger().merge(
            scielo_docs=[doc_a, doc_b],
            openalex_matches=[],
        )

        self.assertIn("scl", merged.oca_data["merge_trace"]["scielo_matches"]["collections"])
        self.assertIn("col", merged.oca_data["merge_trace"]["scielo_matches"]["collections"])
        self.assertEqual(len(merged.oca_data["merge_trace"]["scielo_matches"]["doc_ids"]), 2)

    def test_merge_enriches_with_openalex_citation_count(self):
        primary = SilverDocument(
            doc_id="S1",
            type="article",
            title="SciELO title",
            doi="10.1590/scielo",
            ids={"doi": "10.1590/scielo"},
            citation_count=5,
            oca_data={"scope": ["scielo"]},
        )
        enrichment = SilverDocument(
            doc_id="https://openalex.org/W1",
            type="article",
            title="OpenAlex title",
            doi="10.1590/openalex",
            citation_count=10,
            oca_data={"scope": ["openalex"]},
        )

        merged = SilverMerger().merge(
            scielo_docs=[primary],
            openalex_matches=[(enrichment, "doi", "high", {})],
        )

        self.assertEqual(merged.citation_count, 15)
        self.assertEqual(merged.doi, "10.1590/scielo")
        self.assertEqual(merged.ids["doi"], "10.1590/scielo")

    def test_merge_enriches_with_openalex_referenced_works(self):
        primary = SilverDocument(
            doc_id="S1",
            type="article",
            referenced_works=["https://openalex.org/W10"],
            oca_data={"scope": ["scielo"]},
        )
        enrichment = SilverDocument(
            doc_id="https://openalex.org/W1",
            type="article",
            referenced_works=["https://openalex.org/W20"],
            oca_data={"scope": ["openalex"]},
        )

        merged = SilverMerger().merge(
            scielo_docs=[primary],
            openalex_matches=[(enrichment, "doi", "high", {})],
        )

        self.assertIn("https://openalex.org/W10", merged.referenced_works)
        self.assertIn("https://openalex.org/W20", merged.referenced_works)

    def test_merge_preserves_multiple_openalex_language_matches(self):
        primary = SilverDocument(
            doc_id="S1",
            type="article",
            title="SciELO title",
            oca_data={"scope": ["scielo"]},
        )
        enrichments = [
            SilverDocument(
                doc_id="https://openalex.org/W1",
                type="article",
                title="OpenAlex EN",
                language=["en"],
                openalex_id="https://openalex.org/W1",
                ids={"openalex_with_lang": [{"language": "en", "openalex": "https://openalex.org/W1"}]},
                oca_data={"scope": ["openalex"]},
            ),
            SilverDocument(
                doc_id="https://openalex.org/W2",
                type="article",
                title="OpenAlex PT",
                language=["pt"],
                openalex_id="https://openalex.org/W2",
                ids={"openalex_with_lang": [{"language": "pt", "openalex": "https://openalex.org/W2"}]},
                oca_data={"scope": ["openalex"]},
            ),
            SilverDocument(
                doc_id="https://openalex.org/W3",
                type="article",
                title="OpenAlex ES",
                language=["es"],
                openalex_id="https://openalex.org/W3",
                ids={"openalex_with_lang": [{"language": "es", "openalex": "https://openalex.org/W3"}]},
                oca_data={"scope": ["openalex"]},
            ),
        ]

        merged = SilverMerger().merge(
            scielo_docs=[primary],
            openalex_matches=[(doc, "doi", "high", {}) for doc in enrichments],
        )
        indexed = merged.to_index_dict()

        self.assertEqual(
            indexed["ids"]["openalex"],
            ["https://openalex.org/W1", "https://openalex.org/W2", "https://openalex.org/W3"],
        )
        self.assertEqual(
            indexed["oca_data"]["openalex"]["ids"],
            ["https://openalex.org/W1", "https://openalex.org/W2", "https://openalex.org/W3"],
        )
        self.assertEqual(
            {item["language"] for item in indexed["ids"]["openalex_with_lang"]},
            {"en", "pt", "es"},
        )
        self.assertEqual(len(indexed["oca_data"]["merge_trace"]["openalex_matches"]), 3)

    def test_merge_enriches_missing_access_url_and_biblio_from_openalex(self):
        primary = SilverDocument(
            doc_id="B1",
            type="book",
            title="SciELO book",
            biblio={"volume": "1"},
            source={"title": "SciELO Books"},
            oca_data={"scope": ["scielo"]},
        )
        enrichment = SilverDocument(
            doc_id="https://openalex.org/W1",
            type="book",
            title="OpenAlex book",
            content_url="https://example.org/book.pdf",
            content_url_with_lang=[
                {"language": "pt", "content_url": "https://example.org/book.pdf"}
            ],
            is_open_access=True,
            open_access_status="gold",
            biblio={
                "volume": "99",
                "issue": "2",
                "first_page": "10",
                "last_page": "20",
            },
            source={
                "landing_page_url": "https://example.org/book",
                "is_open_access": True,
            },
            openalex_id="https://openalex.org/W1",
            oca_data={"scope": ["openalex"]},
        )

        merged = SilverMerger().merge(
            scielo_docs=[primary],
            openalex_matches=[(enrichment, "doi", "high", {})],
        )
        indexed = merged.to_index_dict()

        self.assertEqual(indexed["content_url"], "https://example.org/book.pdf")
        self.assertEqual(
            indexed["content_url_with_lang"],
            [{"language": "pt", "content_url": "https://example.org/book.pdf"}],
        )
        self.assertIs(indexed["is_open_access"], True)
        self.assertEqual(indexed["open_access_status"], "gold")
        self.assertEqual(indexed["biblio"]["volume"], "1")
        self.assertEqual(indexed["biblio"]["issue"], "2")
        self.assertEqual(indexed["biblio"]["first_page"], "10")
        self.assertEqual(indexed["biblio"]["last_page"], "20")
        self.assertEqual(indexed["source"]["title"], "SciELO Books")
        self.assertEqual(indexed["source"]["landing_page_url"], "https://example.org/book")
        self.assertIs(indexed["source"]["is_open_access"], True)

    def test_merge_does_not_overwrite_scielo_access_url_or_biblio(self):
        primary = SilverDocument(
            doc_id="B1",
            type="book",
            title="SciELO book",
            content_url="https://scielo.org/book.pdf",
            content_url_with_lang=[
                {"language": "pt", "content_url": "https://scielo.org/book.pdf"}
            ],
            is_open_access=False,
            open_access_status="closed",
            biblio={
                "volume": "1",
                "issue": "1",
                "first_page": "1",
                "last_page": "5",
            },
            source={
                "title": "SciELO Books",
                "landing_page_url": "https://scielo.org/book",
                "is_open_access": False,
            },
            oca_data={"scope": ["scielo"]},
        )
        enrichment = SilverDocument(
            doc_id="https://openalex.org/W1",
            type="book",
            title="OpenAlex book",
            content_url="https://example.org/book.pdf",
            content_url_with_lang=[
                {"language": "pt", "content_url": "https://example.org/book.pdf"}
            ],
            is_open_access=True,
            open_access_status="gold",
            biblio={
                "volume": "99",
                "issue": "2",
                "first_page": "10",
                "last_page": "20",
            },
            source={
                "landing_page_url": "https://example.org/book",
                "is_open_access": True,
            },
            openalex_id="https://openalex.org/W1",
            oca_data={"scope": ["openalex"]},
        )

        merged = SilverMerger().merge(
            scielo_docs=[primary],
            openalex_matches=[(enrichment, "doi", "high", {})],
        )
        indexed = merged.to_index_dict()

        self.assertEqual(indexed["content_url"], "https://scielo.org/book.pdf")
        self.assertEqual(
            indexed["content_url_with_lang"],
            [{"language": "pt", "content_url": "https://scielo.org/book.pdf"}],
        )
        self.assertIs(indexed["is_open_access"], False)
        self.assertEqual(indexed["open_access_status"], "closed")
        self.assertEqual(
            indexed["biblio"],
            {"volume": "1", "issue": "1", "first_page": "1", "last_page": "5"},
        )
        self.assertEqual(indexed["source"]["landing_page_url"], "https://scielo.org/book")
        self.assertIs(indexed["source"]["is_open_access"], False)

    def test_merge_empty_scielo_docs_raises(self):
        with self.assertRaisesRegex(ValueError, "At least one SciELO"):
            SilverMerger().merge(scielo_docs=[], openalex_matches=[])
