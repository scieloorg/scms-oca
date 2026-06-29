import json
from pathlib import Path
from unittest.mock import Mock

from django.apps import apps

from etl.deduplicator.helpers import can_compare, rules_for_pair
from etl.deduplicator.openalex import OpenAlexMatcher
from etl.deduplicator.scielo import SciELODeduplicator
from etl.models import EtlPipelineConfig
from etl.pipeline import OpenSearchETLPipeline
from etl.tests.base import EtlTestCase


FIXTURES_DIR = Path(apps.get_app_config("etl").path) / "tests" / "fixtures"


def make_deduplicator(document_type):
    config = EtlPipelineConfig.objects.get_enabled_by_name(document_type)
    return SciELODeduplicator(config.to_rules())


def make_matcher(document_type):
    matcher = OpenAlexMatcher.__new__(OpenAlexMatcher)
    matcher.rules = EtlPipelineConfig.objects.get_enabled_by_name(document_type).to_rules()
    matcher.input_openalex_index = "silver_scientific_production"
    return matcher


class DocumentRulesTests(EtlTestCase):

    _match_cases = None
    _silver_articles = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._match_cases = json.loads(
            (FIXTURES_DIR / "openalex_match_cases.json").read_text()
        )
        cls._silver_articles = json.loads(
            (FIXTURES_DIR / "silver_article_cases.json").read_text()
        )

    @staticmethod
    def _search_response(candidates):
        return {
            "hits": {
                "hits": [
                    {"_id": candidate.get("doc_id"), "_source": candidate}
                    for candidate in candidates
                ]
            }
        }

    @staticmethod
    def _openalex_ids(indexed_ids):
        oa = indexed_ids.get("openalex")
        if isinstance(oa, list):
            return oa
        if oa:
            return [oa]
        return []

    @classmethod
    def _match_openalex_ids(cls, matches):
        ids = []
        for silver_doc, _strategy, _confidence, _validation in matches:
            ids.extend(cls._openalex_ids(silver_doc.to_index_dict().get("ids") or {}))
        return ids

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

    def test_document_type_openalex_match_strategies_are_domain_specific(self):
        self.assertEqual(
            EtlPipelineConfig.objects.get_enabled_by_name("article").to_rules()[
                "openalex_match_strategies"
            ],
            ["doi", "title"],
        )
        self.assertEqual(
            EtlPipelineConfig.objects.get_enabled_by_name("book").to_rules()[
                "openalex_match_strategies"
            ],
            ["doi", "isbn", "title"],
        )
        self.assertEqual(
            EtlPipelineConfig.objects.get_enabled_by_name("book-chapter").to_rules()[
                "openalex_match_strategies"
            ],
            ["doi", "isbn", "title"],
        )

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

    def test_openalex_doi_search_uses_exact_or_prefix_queries(self):
        matcher = make_matcher("article")
        matcher.client = Mock()
        matcher.client.client.search.return_value = {"hits": {"hits": []}}

        matcher._search_openalex_by_doi(
            "10.1590/0034-7167.202578SUPL101",
            {"publication_year": 2025},
        )

        body = matcher.client.client.search.call_args.kwargs["body"]
        self.assertNotIn("wildcard", str(body))
        doi_filter = body["query"]["bool"]["filter"][0]["bool"]
        self.assertEqual(doi_filter["minimum_should_match"], 1)
        self.assertEqual(
            body["query"]["bool"]["must_not"],
            [{"term": {"is_xpac": True}}],
        )
        self.assertIn(
            {"range": {"publication_year": {"gte": 2024, "lte": 2026}}},
            body["query"]["bool"]["filter"],
        )
        self.assertIn(
            {
                "prefix": {
                    "ids.doi": (
                        "https://doi.org/10.1590/0034-7167.202578supl101"
                    )
                }
            },
            doi_filter["should"],
        )
        self.assertIn(
            {"term": {"ids.doi": "10.1590/0034-7167.202578supl101"}},
            doi_filter["should"],
        )

    def test_openalex_title_strategy_runs_when_doi_lookup_has_no_match(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()
        matcher.client.client.search.side_effect = [
            {"hits": {"hits": []}},
            {
                "hits": {
                    "hits": [
                        {"_source": self._openalex_article("https://openalex.org/W1", "en", "")},
                    ]
                }
            },
        ]

        matches = matcher.find_matches(
            [
                {
                    "type": "article",
                    "publication_year": 2025,
                    "ids": {"doi": "10.1590/unmatched"},
                    "title": "Ethical dilemmas in nursing professionals' work",
                    "source_issns": ["0034-7167", "1984-0446"],
                }
            ],
            max_candidates=3,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][1], "title_year_author")
        self.assertEqual(matcher.client.client.search.call_count, 2)

    def test_openalex_isbn_search_only_uses_bibliographic_isbn_fields(self):
        matcher = make_matcher("book")
        matcher.client = Mock()
        matcher.client.client.search.return_value = {"hits": {"hits": []}}

        matcher._search_openalex_by_isbn(
            ["9786500000001"],
            {"publication_year": 2025},
        )

        body = matcher.client.client.search.call_args.kwargs["body"]
        self.assertNotIn("issn", str(body).lower())
        self.assertIn(
            {"terms": {"ids.isbn": ["9786500000001"]}},
            body["query"]["bool"]["should"],
        )
        self.assertIn(
            {"terms": {"parent_book.ids.isbn": ["9786500000001"]}},
            body["query"]["bool"]["should"],
        )
        self.assertIn(
            {"terms": {"biblio.isbns": ["9786500000001"]}},
            body["query"]["bool"]["should"],
        )

    def test_openalex_title_search_respects_source_issn_field_only(self):
        matcher = make_matcher("article")
        matcher.client = Mock()
        matcher.client.client.search.return_value = {"hits": {"hits": []}}

        cases = [
            ("source_issns", ["0034-7167", "1984-0446"], True),
            ("journal_issns", ["0034-7167", "1984-0446"], False),
        ]
        for field, issns, expect_should in cases:
            with self.subTest(issn_field=field):
                scielo_doc = {
                    "publication_year": 2025,
                    "title": "Ethical dilemmas in nursing professionals' work",
                    field: issns[:],
                }
                matcher.client.client.search.reset_mock()
                matcher._search_openalex_by_title_year(scielo_doc)

                body = matcher.client.client.search.call_args.kwargs["body"]

                self.assertNotIn("isbn", str(body).lower())
                self.assertIn(
                    {
                        "match": {
                            "title": {
                                "query": "Ethical dilemmas in nursing professionals' work",
                                "minimum_should_match": "90%",
                                "fuzziness": "AUTO",
                            }
                        }
                    },
                    body["query"]["bool"]["must"],
                )

                if expect_should:
                    self.assertEqual(
                        body["query"]["bool"]["should"],
                        [{"terms": {"source.issns": issns}}],
                    )
                    self.assertEqual(body["query"]["bool"]["minimum_should_match"], 1)
                else:
                    self.assertNotIn("should", body["query"]["bool"])
                    self.assertNotIn("minimum_should_match", body["query"]["bool"])

    def test_openalex_title_strategy_returns_validated_issn_match(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()
        matcher.client.client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": self._openalex_article("https://openalex.org/W1", "en", "")},
                ]
            }
        }

        matches = matcher.find_matches(
            [
                {
                    "type": "article",
                    "publication_year": 2025,
                    "title": "Ethical dilemmas in nursing professionals' work",
                    "source_issns": ["0034-7167", "1984-0446"],
                }
            ],
            max_candidates=3,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][1], "title_year_author")
        self.assertIn("issn_match_2", matches[0][3]["reasons"])

    def test_openalex_title_strategy_rejects_low_title_similarity(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()
        matcher.client.client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": self._openalex_article("https://openalex.org/W1", "en", "")},
                ]
            }
        }

        matches = matcher.find_matches(
            [
                {
                    "type": "article",
                    "publication_year": 2025,
                    "title": "Unrelated clinical protocol for dentistry",
                    "source_issns": ["0034-7167", "1984-0446"],
                }
            ],
            max_candidates=3,
        )

        self.assertEqual(matches, [])

    def test_openalex_issn_is_not_an_article_match_strategy(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()
        matcher.client.client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": self._openalex_article("https://openalex.org/W1", "en", "")},
                ]
            }
        }

        matches = matcher.find_matches(
            [
                {
                    "type": "article",
                    "publication_year": 2025,
                    "source_issns": ["0034-7167", "1984-0446"],
                }
            ],
            max_candidates=3,
        )

        self.assertEqual(matches, [])
        matcher.client.client.search.assert_not_called()

    def test_openalex_match_skips_year_outside_configured_raw_range(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()

        matches = matcher.find_matches(
            [
                {
                    "type": "article",
                    "publication_year": 2017,
                    "ids": {"doi": "10.1590/0034-7167.202578SUPL101"},
                }
            ],
            max_candidates=3,
        )

        self.assertEqual(matches, [])
        matcher.client.client.search.assert_not_called()

    def test_openalex_match_keeps_year_adjacent_to_configured_raw_range(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()
        matcher.client.client.search.return_value = {"hits": {"hits": []}}

        matcher.find_matches(
            [
                {
                    "type": "article",
                    "publication_year": 2018,
                    "ids": {"doi": "10.1590/0034-7167.202578SUPL101"},
                }
            ],
            max_candidates=3,
        )

        matcher.client.client.search.assert_called_once()

    def test_openalex_match_skips_missing_scielo_publication_year(self):
        matcher = make_matcher("article")
        matcher.input_openalex_index = "raw_openalex_works"
        matcher.client = Mock()

        matches = matcher.find_matches(
            [
                {
                    "type": "article",
                    "ids": {"doi": "10.1590/0034-7167.202578SUPL101"},
                }
            ],
            max_candidates=3,
        )

        self.assertEqual(matches, [])
        matcher.client.client.search.assert_not_called()

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
