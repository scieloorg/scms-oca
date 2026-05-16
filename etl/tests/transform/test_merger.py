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

    def test_merge_empty_scielo_docs_raises(self):
        with self.assertRaisesRegex(ValueError, "At least one SciELO"):
            SilverMerger().merge(scielo_docs=[], openalex_matches=[])
