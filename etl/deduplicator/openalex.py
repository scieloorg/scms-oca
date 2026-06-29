from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from etl.client import OpenSearchClient
from etl.transform.normalizers import normalize_doi, normalize_text
from etl.deduplicator.helpers import (
    calculate_similarity,
    select_primary_scielo_doc,
)
from etl.transform.extractors import (
    extract_doi,
    extract_isbns,
    extract_issns,
    extract_source,
    extract_titles,
)

logger = logging.getLogger(__name__)


class OpenAlexMatcher:

    def __init__(
        self,
        opensearch_host: str | None = None,
        opensearch_port: int | None = None,
        opensearch_url: str | None = None,
        input_openalex_index: str = "silver_scientific_production",
        rules: dict | None = None,
    ):
        if rules is None:
            raise ValueError("OpenAlexMatcher requires explicit document rules")

        self.client = OpenSearchClient(host=opensearch_host, port=opensearch_port, url=opensearch_url)
        self.input_openalex_index = input_openalex_index
        self.rules = rules

    def find_matches(
        self,
        scielo_group: List[Dict[str, Any]],
        max_candidates: int = 10,
    ) -> List[Tuple[Dict[str, Any], str, float, Dict[str, Any]]]:
        if not scielo_group:
            return []

        primary = select_primary_scielo_doc(scielo_group)
        rules = self.rules
        if not self._can_search_openalex(primary):
            logger.debug(
                "Skipping OpenAlex match lookup for SciELO doc outside configured query scope"
            )
            return []

        matches = []

        for strategy in rules["openalex_match_strategies"]:
            if strategy == "doi":
                matches.extend(self._try_openalex_by_doi(primary, max_candidates))
            elif strategy == "isbn" and not matches:
                matches.extend(self._try_openalex_by_isbn(primary, max_candidates))
            elif strategy == "title" and not matches:
                matches.extend(self._try_openalex_by_title(primary, max_candidates))

        matches = self._deduplicate_openalex_matches(matches)
        logger.debug("Found %s validated OpenAlex matches for SciELO group", len(matches))
        return matches

    def _try_openalex_by_doi(self, primary: dict, max_candidates: int) -> list:
        doi = extract_doi(primary)
        if not doi or not (doi_stz := normalize_doi(doi)):
            return []

        matches = []
        for candidate in self._search_openalex_by_doi(doi_stz, primary)[:max_candidates]:
            candidate_doi = normalize_doi(extract_doi(candidate))
            if candidate_doi != doi_stz:
                continue

            is_valid, confidence, validation = self._validate_openalex_match(primary, candidate)
            if is_valid:
                matches.append((candidate, "doi", confidence, validation))

        return matches

    def _try_openalex_by_isbn(self, primary: dict, max_candidates: int) -> list:
        isbns = extract_isbns(primary)
        if not isbns:
            return []

        matches = []
        for candidate in self._search_openalex_by_isbn(isbns, primary)[:max_candidates]:
            is_valid, confidence, validation = self._validate_openalex_match(primary, candidate)
            if is_valid:
                matches.append((candidate, "isbn", confidence, validation))
        return matches

    def _try_openalex_by_title(self, primary: dict, max_candidates: int) -> list:
        if extract_isbns(primary):
            return []

        matches = []
        for candidate in self._search_openalex_by_title_year(primary)[:max_candidates]:
            is_valid, confidence, validation = self._validate_openalex_match(
                primary,
                candidate,
                use_strict_validation=True,
            )
            if is_valid:
                matches.append((candidate, "title_year_author", confidence, validation))
        return matches

    def _deduplicate_openalex_matches(self, matches: list) -> list:
        if not matches:
            return matches

        seen = set()
        deduped = []
        for match in matches:
            candidate_id = match[0].get("id") or match[0].get("openalex_id")
            if not candidate_id or candidate_id not in seen:
                if candidate_id:
                    seen.add(candidate_id)
                deduped.append(match)
        return deduped

    def _can_search_openalex(self, scielo_doc: dict) -> bool:
        year = self._publication_year(scielo_doc)
        if year is None:
            return False

        query_rules = self.rules.get("openalex_query") or {}
        min_year = query_rules.get("publication_year_min")
        max_year = query_rules.get("publication_year_max")
        if min_year is None and max_year is None:
            return True

        tolerance = self._year_tolerance()
        lower = year - tolerance
        upper = year + tolerance

        try:
            if min_year is not None and upper < int(min_year):
                return False
            if max_year is not None and lower > int(max_year):
                return False
        except (TypeError, ValueError):
            logger.warning("Invalid OpenAlex publication year query bounds: %s", query_rules)
            return True

        return True

    def _publication_year(self, doc: dict) -> int | None:
        try:
            return int(doc.get("publication_year"))
        except (TypeError, ValueError):
            return None

    def _year_tolerance(self) -> int:
        validation_rules = self.rules.get("openalex_validation") or {}
        try:
            return int(validation_rules.get("year_tolerance", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _apply_openalex_query_constraints(
        self,
        query: dict[str, Any],
        scielo_doc: dict[str, Any],
    ) -> dict[str, Any]:
        bool_query = query.setdefault("bool", {})

        bool_query.setdefault("filter", []).append(
            {
                "bool": {
                    "should": [
                        {"exists": {"field": "ids.openalex"}},
                        {"exists": {"field": "openalex_id"}},
                        {"exists": {"field": "oca_data.openalex.ids"}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

        query_rules = self.rules.get("openalex_query") or {}

        if query_rules.get("exclude_is_xpac"):
            bool_query.setdefault("must_not", []).append({"term": {"is_xpac": True}})

        year = self._publication_year(scielo_doc)
        if year is not None:
            tolerance = self._year_tolerance()
            bool_query.setdefault("filter", []).append(
                {"range": {"publication_year": {"gte": year - tolerance, "lte": year + tolerance}}}
            )

        return query

    def _search_openalex_by_doi(
        self,
        doi: str,
        scielo_doc: Dict[str, Any],
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        normalized_doi = normalize_doi(doi)
        if not normalized_doi:
            logger.warning("Invalid DOI after normalization: %s", doi)
            return []

        query = {
            "bool": {
                "filter": [
                    {
                        "bool": {
                            "should": self._doi_exact_or_prefix_queries(normalized_doi),
                            "minimum_should_match": 1,
                        }
                    }
                ]
            }
        }
        self._apply_openalex_query_constraints(query, scielo_doc)

        try:
            response = self.client.client.search(
                index=self.input_openalex_index,
                body={"query": query, "size": size},
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as exc:
            logger.error("Error searching OpenAlex by DOI: %s", exc)
            return []

    def _doi_exact_or_prefix_queries(self, normalized_doi: str) -> list[dict[str, Any]]:
        doi_values = [
            normalized_doi,
            f"https://doi.org/{normalized_doi}",
            f"http://doi.org/{normalized_doi}",
            f"https://dx.doi.org/{normalized_doi}",
            f"http://dx.doi.org/{normalized_doi}",
        ]
        fields = ["ids.doi", "ids.doi_with_lang.doi"]

        queries: list[dict[str, Any]] = []
        for field in fields:
            queries.extend({"term": {field: value}} for value in doi_values)
            queries.extend({"prefix": {field: value}} for value in doi_values)

        return queries

    def _search_openalex_by_isbn(
        self,
        isbns: List[str],
        scielo_doc: Dict[str, Any],
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        query = {
            "bool": {
                "should": [
                    {"terms": {"ids.isbn": isbns}},
                    {"terms": {"parent_book.ids.isbn": isbns}},
                    {"terms": {"parent_book.ids.eisbn": isbns}},
                    {"terms": {"biblio.isbn": isbns}},
                    {"terms": {"biblio.isbns": isbns}},
                ],
                "minimum_should_match": 1,
            }
        }
        self._apply_openalex_query_constraints(query, scielo_doc)

        try:
            response = self.client.client.search(
                index=self.input_openalex_index,
                body={"query": query, "size": size},
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as exc:
            logger.error("Error searching OpenAlex by ISBN: %s", exc)
            return []

    def _search_openalex_by_title_year(
        self,
        scielo_doc: Dict[str, Any],
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        title = scielo_doc.get("title", "")
        issns = scielo_doc.get("source_issns") or []
        if not title:
            return []

        query = {
            "bool": {
                "must": [
                    {
                        "match": {
                            "title": {
                                "query": title,
                                "minimum_should_match": "90%",
                                "fuzziness": "AUTO",
                            }
                        }
                    }
                ]
            }
        }
        self._apply_openalex_query_constraints(query, scielo_doc)

        if issns:
            query["bool"]["should"] = self._source_issn_queries(issns)
            query["bool"]["minimum_should_match"] = 1

        try:
            response = self.client.client.search(
                index=self.input_openalex_index,
                body={"query": query, "size": size},
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as exc:
            logger.error("Error searching OpenAlex by title: %s", exc)
            return []

    def _source_issn_queries(self, issns: list[str]) -> list[dict[str, Any]]:
        return [
            {"terms": {"source.issns": issns}},
        ]

    def _validate_openalex_match(
        self,
        scielo_doc: Dict[str, Any],
        openalex_doc: Dict[str, Any],
        use_strict_validation: bool = False,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        reasons = []
        confidence_score = 0
        validation_rules = self.rules["openalex_validation"]

        scl_doi = normalize_doi(extract_doi(scielo_doc))
        oa_doi = normalize_doi(extract_doi(openalex_doc))
        doi_match = bool(scl_doi and oa_doi and scl_doi == oa_doi)
        if doi_match:
            confidence_score += validation_rules["doi_score"]
            reasons.append("doi_match")

        scl_year = scielo_doc.get("publication_year")
        oa_year = openalex_doc.get("publication_year")
        if validation_rules["require_openalex_year"] and oa_year is None:
            reasons.append("openalex_missing_year")
            return False, "rejected", {"reasons": reasons, "score": 0}

        try:
            scl_year = int(scl_year) if scl_year is not None else None
            oa_year = int(oa_year) if oa_year is not None else None
        except (ValueError, TypeError):
            reasons.append("invalid_year_format")
            return False, "rejected", {"reasons": reasons, "score": 0}

        year_diff = 999 if scl_year is None or oa_year is None else abs(scl_year - oa_year)
        if year_diff == 0:
            confidence_score += validation_rules["year_exact_score"]
            reasons.append("year_exact_match")
        elif year_diff <= validation_rules["year_tolerance"]:
            confidence_score += validation_rules["year_close_score"]
            reasons.append(f"year_close_{year_diff}yr")
        else:
            reasons.append(f"year_mismatch_{year_diff}yr")
            return False, "rejected", {"reasons": reasons, "score": confidence_score}

        scl_isbns = set(extract_isbns(scielo_doc))
        oa_isbns = set(extract_isbns(openalex_doc))
        isbn_intersection = scl_isbns & oa_isbns
        if isbn_intersection:
            confidence_score += validation_rules["isbn_score"]
            reasons.append(f"isbn_match_{len(isbn_intersection)}")

        scl_issns = set(extract_issns(scielo_doc))
        oa_source = extract_source(openalex_doc)
        oa_issns = set(extract_issns(openalex_doc))
        issn_intersection = scl_issns & oa_issns

        scl_journal_title = normalize_text(scielo_doc.get("journal_title", "") or "")
        scl_journal_title = scl_journal_title.lower() if scl_journal_title else ""
        oa_journal_title = normalize_text(
            oa_source.get("title", "") or oa_source.get("display_name", "") or ""
        )
        oa_journal_title = oa_journal_title.lower() if oa_journal_title else ""
        journal_similarity = calculate_similarity(scl_journal_title, oa_journal_title)

        source_matched = False
        if issn_intersection:
            source_matched = True
            confidence_score += validation_rules["source_id_score"]
            reasons.append(f"issn_match_{len(issn_intersection)}")
        elif journal_similarity >= validation_rules["source_similarity_threshold"]:
            source_matched = True
            confidence_score += validation_rules["source_title_score"]
            reasons.append(f"journal_title_similar_{journal_similarity:.2f}")
        else:
            reasons.append("journal_mismatch")
            if validation_rules["require_source_match"]:
                return False, "rejected", {"reasons": reasons, "score": confidence_score}

        scl_titles = extract_titles(scielo_doc)
        oa_titles = extract_titles(openalex_doc)
        article_title_sim = max(
            (calculate_similarity(scl_t, oa_t) for scl_t in scl_titles for oa_t in oa_titles),
            default=0.0,
        )

        if (
            isbn_intersection
            and validation_rules["isbn_requires_title_match"]
            and article_title_sim < validation_rules["isbn_title_threshold"]
        ):
            reasons.append(f"chapter_title_too_low_for_isbn_{article_title_sim:.2f}")
            return (
                False,
                "low_confidence",
                {"reasons": reasons, "score": confidence_score, "title_similarity": article_title_sim},
            )

        if article_title_sim >= validation_rules["title_match_threshold"]:
            confidence_score += validation_rules["title_score"]
            reasons.append(f"article_title_match_{article_title_sim:.2f}")
        else:
            reasons.append(f"article_title_low_sim_{article_title_sim:.2f}")
            if (
                not doi_match
                and scl_titles
                and oa_titles
                and article_title_sim < validation_rules["title_reject_threshold"]
            ):
                return (
                    False,
                    "low_confidence",
                    {
                        "reasons": reasons,
                        "score": confidence_score,
                        "year_check": "exact_match" if year_diff == 0 else f"close_{year_diff}yr",
                        "doi_check": "match" if doi_match else "mismatch",
                        "journal_check": "issn_match" if issn_intersection else (
                            "title_similar" if source_matched else "mismatch"
                        ),
                        "isbn_check": "isbn_match" if isbn_intersection else "mismatch",
                        "title_similarity": article_title_sim,
                    },
                )

            if confidence_score < validation_rules["min_score"]:
                return (
                    False,
                    "low_confidence",
                    {"reasons": reasons, "score": confidence_score, "title_similarity": article_title_sim},
                )

        threshold = validation_rules["strict_min_score"] if use_strict_validation else validation_rules["min_score"]
        confidence_level = "high" if confidence_score >= 70 else ("medium" if confidence_score >= threshold else "low")
        is_valid = confidence_score >= threshold

        details = {
            "reasons": reasons,
            "score": confidence_score,
            "year_check": "exact_match" if year_diff == 0 else f"close_{year_diff}yr",
            "doi_check": "match" if doi_match else "mismatch",
            "journal_check": "issn_match" if issn_intersection else ("title_similar" if source_matched else "mismatch"),
            "isbn_check": "isbn_match" if isbn_intersection else "mismatch",
            "title_similarity": article_title_sim,
        }
        return is_valid, confidence_level, details
