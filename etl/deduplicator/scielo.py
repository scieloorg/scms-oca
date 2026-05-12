from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from etl.transform.normalizers import stz_doi
from etl.deduplicator.helpers import (
    calculate_similarity,
    can_compare,
    rules_for_pair,
)
from etl.transform.extractors import (
    extract_doi,
    extract_issns,
    extract_scielo_id,
    get_normalized_titles,
)
from etl.pipeline.defaults import DocumentRules

logger = logging.getLogger(__name__)


class UnionFind:
    """Data structure for managing disjoint sets."""

    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i: int, j: int) -> None:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


class SciELODeduplicator:

    def __init__(self, rules: DocumentRules):
        self.rules = rules

    def find_duplicates(self, articles: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        if len(articles) <= 1:
            return {0: articles} if articles else {}

        logger.info("Starting SciELO deduplication for %s articles...", len(articles))

        uf = UnionFind(len(articles))
        doi_to_indices: Dict[str, List[int]] = defaultdict(list)
        pid_to_indices: Dict[str, List[int]] = defaultdict(list)

        for idx, article in enumerate(articles):
            if doi_stz := stz_doi(extract_doi(article)):
                doi_to_indices[doi_stz].append(idx)
            if pid := extract_scielo_id(article):
                pid_to_indices[pid].append(idx)

        if "doi" in self.rules.scielo_dedup_strategies:
            self._merge_by_doi(articles, doi_to_indices, uf)
        if "pid" in self.rules.scielo_dedup_strategies:
            self._merge_by_pid(articles, pid_to_indices, uf)
        if "fuzzy" in self.rules.scielo_dedup_strategies:
            self._merge_by_title_fuzzy(
                articles,
                uf,
                min_similarity=self.rules.fuzzy_min_similarity,
                year_tolerance=self.rules.fuzzy_year_tolerance,
            )

        components: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for i in range(len(articles)):
            components[uf.find(i)].append(articles[i])

        merged_count = sum(1 for group in components.values() if len(group) > 1)
        logger.info(
            "SciELO deduplication complete: %s articles -> %s groups (%s groups with duplicates)",
            len(articles),
            len(components),
            merged_count,
        )
        return components

    def _merge_by_doi(
        self,
        articles: List[Dict[str, Any]],
        doi_to_indices: Dict[str, List[int]],
        uf: UnionFind,
    ) -> None:
        for _doi, indices in doi_to_indices.items():
            if len(indices) < 2:
                continue

            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    idx_i, idx_j = indices[i], indices[j]
                    if not can_compare(articles[idx_i], articles[idx_j], self.rules):
                        continue

                    rules = rules_for_pair(articles[idx_i], articles[idx_j], self.rules)
                    titles_i = set(get_normalized_titles(articles[idx_i]))
                    titles_j = set(get_normalized_titles(articles[idx_j]))
                    if (titles_i & titles_j) or not rules.doi_requires_title_overlap:
                        uf.union(idx_i, idx_j)

    def _merge_by_pid(
        self,
        articles: List[Dict[str, Any]],
        pid_to_indices: Dict[str, List[int]],
        uf: UnionFind,
    ) -> None:
        for _pid, indices in pid_to_indices.items():
            if len(indices) < 2:
                continue

            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    idx_i, idx_j = indices[i], indices[j]
                    if uf.find(idx_i) == uf.find(idx_j):
                        continue

                    art_i, art_j = articles[idx_i], articles[idx_j]
                    if not can_compare(art_i, art_j, self.rules):
                        continue

                    rules = rules_for_pair(art_i, art_j, self.rules)
                    year_match = True
                    if rules.pid_requires_year_match:
                        try:
                            year_i = int(art_i.get("publication_year", 0) or 0)
                            year_j = int(art_j.get("publication_year", 0) or 0)
                            year_match = year_i == year_j and year_i > 0
                        except (ValueError, TypeError):
                            year_match = False

                    same_source = True
                    if rules.pid_requires_source_match:
                        issns_i = set(extract_issns(art_i))
                        issns_j = set(extract_issns(art_j))
                        same_source = bool(
                            (issns_i & issns_j)
                            or (
                                art_i.get("journal_title") == art_j.get("journal_title")
                                and art_i.get("journal_title")
                            )
                        )

                    titles_i = set(get_normalized_titles(art_i))
                    titles_j = set(get_normalized_titles(art_j))
                    title_match = bool(titles_i & titles_j) or not rules.pid_requires_title_overlap

                    if year_match and same_source and title_match:
                        uf.union(idx_i, idx_j)

    def _merge_by_title_fuzzy(
        self,
        articles: List[Dict[str, Any]],
        uf: UnionFind,
        min_similarity: float = 0.85,
        year_tolerance: int = 1,
    ) -> None:
        year_groups = defaultdict(list)
        for idx, article in enumerate(articles):
            year = article.get("publication_year")
            if year is not None:
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    continue
                for y in range(year - year_tolerance, year + year_tolerance + 1):
                    year_groups[y].append(idx)

        compared_pairs = set()
        for _year, indices in year_groups.items():
            if len(indices) < 2:
                continue

            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    idx_i, idx_j = indices[i], indices[j]
                    pair_key = tuple(sorted([idx_i, idx_j]))
                    if pair_key in compared_pairs or uf.find(idx_i) == uf.find(idx_j):
                        continue
                    compared_pairs.add(pair_key)

                    art_i, art_j = articles[idx_i], articles[idx_j]
                    if not can_compare(art_i, art_j, self.rules):
                        continue
                    rules = rules_for_pair(art_i, art_j, self.rules)

                    if rules.fuzzy_requires_source_match:
                        issns_i = set(extract_issns(art_i))
                        issns_j = set(extract_issns(art_j))
                        if not (issns_i & issns_j):
                            continue

                    best_similarity = 0.0
                    for t1 in get_normalized_titles(art_i):
                        for t2 in get_normalized_titles(art_j):
                            best_similarity = max(best_similarity, calculate_similarity(t1, t2))

                    try:
                        year_i = int(art_i.get("publication_year", 0) or 0)
                        year_j = int(art_j.get("publication_year", 0) or 0)
                        year_close = abs(year_i - year_j) <= year_tolerance if year_i and year_j else False
                    except (ValueError, TypeError):
                        year_close = False

                    if best_similarity >= min_similarity and year_close:
                        uf.union(idx_i, idx_j)
