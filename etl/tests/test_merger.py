from django.test import SimpleTestCase

from etl.indexing.contracts import SilverDocument
from etl.pipeline.merger import merge


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
            oca_data={"scope": ["openalex"]},
        )

        merged = merge(
            primary,
            [enrichment],
            match_strategy="doi",
            match_confidence="high",
        )

        self.assertEqual(merged.title, "SciELO title")
        self.assertEqual(merged.oca_data["scope"], ["scielo", "openalex"])
        self.assertEqual(merged.oca_data["match_strategy"], "doi")
        self.assertEqual(merged.oca_data["match_confidence"], "high")
        self.assertEqual(
            merged.oca_data["merge_trace"],
            {
                "primary_doc_id": "S1",
                "enrichment_doc_ids": ["https://openalex.org/W1"],
            },
        )
