from unittest.mock import Mock

from django.test import TestCase

from etl.deduplicator.helpers import can_compare, rules_for_pair
from etl.deduplicator.openalex import OpenAlexMatcher
from etl.deduplicator.scielo import SciELODeduplicator
from etl.models import EtlPipelineConfig
from etl.pipeline import OpenSearchETLPipeline


def make_deduplicator(document_type):
    return SciELODeduplicator(EtlPipelineConfig.objects.get_enabled_by_name(document_type).to_rules())


def make_matcher(document_type):
    matcher = OpenAlexMatcher.__new__(OpenAlexMatcher)
    matcher.rules = EtlPipelineConfig.objects.get_enabled_by_name(document_type).to_rules()
    return matcher


class DocumentRulesTests(TestCase):
    def test_can_compare_rejects_doc_type_outside_pipeline_config_rules(self):
        rules = EtlPipelineConfig.objects.get_enabled_by_name("book").to_rules()

        self.assertFalse(
            can_compare(
                {"type": "book"},
                {"type": "book-chapter"},
                rules,
            )
        )

    def test_rules_for_pair_rejects_doc_type_outside_pipeline_config_rules(self):
        rules = EtlPipelineConfig.objects.get_enabled_by_name("book").to_rules()

        with self.assertRaises(ValueError):
            rules_for_pair({"type": "book"}, {"type": "book-chapter"}, rules)

    def test_article_fuzzy_requires_source_match(self):
        deduplicator = make_deduplicator("article")
        groups = deduplicator.find_duplicates(
            [
                {"type": "article", "title": "Same title", "publication_year": 2024},
                {"type": "article", "title": "Same title", "publication_year": 2024},
            ]
        )

        self.assertEqual(len(groups), 2)

    def test_preprint_has_no_internal_scielo_dedup_strategy(self):
        deduplicator = make_deduplicator("preprint")
        groups = deduplicator.find_duplicates(
            [
                {"type": "preprint", "title": "Same preprint title", "publication_year": 2024},
                {"type": "preprint", "title": "Same preprint title", "publication_year": 2024},
            ]
        )

        self.assertEqual(len(groups), 2)

    def test_dataset_does_not_use_fuzzy_strategy(self):
        deduplicator = make_deduplicator("dataset")
        groups = deduplicator.find_duplicates(
            [
                {"type": "dataset", "title": "Same dataset title", "publication_year": 2024},
                {"type": "dataset", "title": "Same dataset title", "publication_year": 2024},
            ]
        )

        self.assertEqual(len(groups), 2)

    def test_non_article_targets_build_unit_groups_without_deduplicator(self):
        pipeline = OpenSearchETLPipeline.__new__(OpenSearchETLPipeline)
        pipeline.pipeline_config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_preprint")
        pipeline.scielo_deduplicator = Mock()
        docs = [{"id": "p1"}, {"id": "p2"}]

        groups = pipeline._build_scielo_groups(docs)

        self.assertEqual(groups, {0: [docs[0]], 1: [docs[1]]})
        pipeline.scielo_deduplicator.find_duplicates.assert_not_called()

    def test_article_target_delegates_grouping_to_deduplicator(self):
        pipeline = OpenSearchETLPipeline.__new__(OpenSearchETLPipeline)
        pipeline.pipeline_config = EtlPipelineConfig.objects.get_for_source("bronze_scielo_articles")
        pipeline.scielo_deduplicator = Mock()
        pipeline.scielo_deduplicator.find_duplicates.return_value = {0: [{"id": "a1"}]}

        groups = pipeline._build_scielo_groups([{"id": "a1"}])

        self.assertEqual(groups, {0: [{"id": "a1"}]})
        pipeline.scielo_deduplicator.find_duplicates.assert_called_once_with(
            articles=[{"id": "a1"}]
        )

    def test_expand_scielo_input_context_keeps_dict_payloads(self):
        pipeline = OpenSearchETLPipeline.__new__(OpenSearchETLPipeline)
        pipeline.input_scielo_index = "bronze_scielo_datasets"
        pipeline.loaded_source_ids = set()
        pipeline.client = Mock()
        pipeline.client.client.search.return_value = {
            "_scroll_id": "scroll-1",
            "hits": {
                "hits": [
                    {
                        "_id": "related-os-id",
                        "_source": {
                            "id": "related-dataset",
                            "ids": {"dataset_id": "dataset-1"},
                            "type": "dataset",
                        },
                    }
                ]
            },
        }
        pipeline.client.client.scroll.return_value = {
            "_scroll_id": "scroll-1",
            "hits": {"hits": []},
        }
        docs = [
            {
                "_os_id": "requested-os-id",
                "id": "requested-dataset",
                "ids": {"dataset_id": "dataset-1"},
                "type": "dataset",
            }
        ]

        expanded = pipeline._expand_scielo_input_context(docs)

        self.assertEqual(len(expanded), 2)
        self.assertTrue(all(isinstance(doc, dict) for doc in expanded))
        self.assertIn("related-os-id", pipeline.loaded_source_ids)
        pipeline.client.client.clear_scroll.assert_called_once_with(scroll_id="scroll-1")

    def test_book_chapter_isbn_requires_chapter_title_match(self):
        matcher = make_matcher("book-chapter")
        is_valid, confidence, details = matcher._validate_openalex_match(
            {
                "type": "book-chapter",
                "title": "Chapter about public health",
                "publication_year": 2024,
                "parent_book": {"ids": {"isbn": "978-65-00-00000-1"}},
            },
            {
                "title": "Completely different chapter",
                "publication_year": 2024,
                "biblio": {"isbn": "978-65-00-00000-1"},
            },
        )

        self.assertFalse(is_valid)
        self.assertEqual(confidence, "low_confidence")
        self.assertIn("chapter_title_too_low_for_isbn", " ".join(details["reasons"]))

    def test_book_accepts_isbn_with_matching_title(self):
        matcher = make_matcher("book")
        is_valid, confidence, _details = matcher._validate_openalex_match(
            {
                "type": "book",
                "title": "Public health in Brazil",
                "publication_year": 2024,
                "ids": {"isbn": "978-65-00-00000-1"},
            },
            {
                "title": "Public health in Brazil",
                "publication_year": 2024,
                "biblio": {"isbn": "978-65-00-00000-1"},
            },
        )

        self.assertTrue(is_valid)
        self.assertEqual(confidence, "high")

    def test_openalex_doi_match_keeps_language_variants_with_same_normalized_doi(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()
        matcher.client.client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": self._openalex_article("https://openalex.org/Wen", "en", "")},
                    {"_source": self._openalex_article("https://openalex.org/Wpt", "pt", "pt")},
                    {"_source": self._openalex_article("https://openalex.org/Wes", "es", "es")},
                ]
            }
        }

        matches = matcher.find_matches(
            [
                {
                    "type": "article",
                    "publication_year": 2025,
                    "ids": {"doi": "10.1590/0034-7167.202578SUPL101"},
                    "title_with_lang": [
                        {"language": "en", "title": "Ethical dilemmas in nursing professionals' work"},
                        {"language": "pt", "title": "Dilemas éticos no trabalho dos profissionais de enfermagem"},
                        {"language": "es", "title": "Dilemas éticos en el trabajo de los profesionales de enfermería"},
                    ],
                    "source_issns": ["0034-7167", "1984-0446"],
                }
            ],
            max_candidates=3,
        )

        self.assertEqual(
            {match[0]["id"] for match in matches},
            {
                "https://openalex.org/Wen",
                "https://openalex.org/Wpt",
                "https://openalex.org/Wes",
            },
        )
        self.assertTrue(all(match[1] == "doi" for match in matches))

    def _openalex_article(self, openalex_id, language, doi_suffix):
        titles = {
            "en": "Ethical dilemmas in nursing professionals' work",
            "pt": "Dilemas éticos no trabalho dos profissionais de enfermagem",
            "es": "Dilemas éticos en el trabajo de los profesionales de enfermería",
        }
        return {
            "id": openalex_id,
            "language": language,
            "doi": f"https://doi.org/10.1590/0034-7167.202578supl101{doi_suffix}",
            "title": titles[language],
            "publication_year": 2025,
            "primary_location": {
                "source": {
                    "issn": ["0034-7167", "1984-0446"],
                    "display_name": "Revista Brasileira de Enfermagem",
                }
            },
        }
