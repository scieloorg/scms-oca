import logging
from collections import defaultdict

from etl.deduplicator.helpers import calculate_similarity
from etl.transform.normalizers import (
    normalize_document_type_for_etl,
    normalize_doi,
)
from etl.transform.extractors import (
    extract_doi,
    extract_issns,
    extract_scielo_document_type,
    extract_scielo_id,
    extract_titles,
)

logger = logging.getLogger(__name__)


class UnionFind:
    """Data structure for managing disjoint sets."""

    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


class SciELODeduplicator:

    def __init__(self, rules):
        self.rules = rules

    def find_duplicates(self, articles):
        if len(articles) <= 1:
            return {0: articles} if articles else {}

        logger.debug("Starting SciELO deduplication for %s articles...", len(articles))

        uf = UnionFind(len(articles))
        doi_to_indices = defaultdict(list)
        pid_to_indices = defaultdict(list)

        for idx, article in enumerate(articles):
            if doi_stz := normalize_doi(extract_doi(article)):
                doi_to_indices[doi_stz].append(idx)
            if pid := extract_scielo_id(article):
                pid_to_indices[pid].append(idx)

        if "doi" in self.rules["scielo_dedup_strategies"]:
            self._merge_by_doi(articles, doi_to_indices, uf)
        if "pid" in self.rules["scielo_dedup_strategies"]:
            self._merge_by_pid(articles, pid_to_indices, uf)
        if "fuzzy" in self.rules["scielo_dedup_strategies"]:
            self._merge_by_title_fuzzy(
                articles,
                uf,
                min_similarity=self.rules["fuzzy_min_similarity"],
                year_tolerance=self.rules["fuzzy_year_tolerance"],
            )

        components = defaultdict(list)
        for i in range(len(articles)):
            components[uf.find(i)].append(articles[i])

        merged_count = sum(1 for group in components.values() if len(group) > 1)
        logger.debug(
            "SciELO deduplication complete: %s articles -> %s groups (%s groups with duplicates)",
            len(articles),
            len(components),
            merged_count,
        )
        return components

    def _merge_by_doi(
        self,
        articles,
        doi_to_indices,
        uf,
    ):
        for _doi, indices in doi_to_indices.items():
            if len(indices) < 2:
                continue

            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    idx_i, idx_j = indices[i], indices[j]
                    if not self._is_deduplicable_scielo_pair(articles[idx_i], articles[idx_j]):
                        continue

                    if self._has_required_context_match(
                        articles[idx_i],
                        articles[idx_j],
                        "doi",
                    ):
                        uf.union(idx_i, idx_j)

    def _merge_by_pid(
        self,
        articles,
        pid_to_indices,
        uf,
    ):
        for _pid, indices in pid_to_indices.items():
            if len(indices) < 2:
                continue

            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    idx_i, idx_j = indices[i], indices[j]
                    if uf.find(idx_i) == uf.find(idx_j):
                        continue

                    art_i, art_j = articles[idx_i], articles[idx_j]
                    if not self._is_deduplicable_scielo_pair(art_i, art_j):
                        continue

                    if self._has_required_context_match(
                        art_i,
                        art_j,
                        "pid",
                    ):
                        uf.union(idx_i, idx_j)

    def _merge_by_title_fuzzy(
        self,
        articles,
        uf,
        min_similarity=0.85,
        year_tolerance=1,
    ):
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
                    if not self._is_deduplicable_scielo_pair(art_i, art_j):
                        continue
                    if self.rules["fuzzy_requires_source_match"]:
                        issns_i = set(extract_issns(art_i))
                        issns_j = set(extract_issns(art_j))
                        if not (issns_i & issns_j):
                            continue

                    best_similarity = 0.0
                    for t1 in extract_titles(art_i):
                        for t2 in extract_titles(art_j):
                            best_similarity = max(best_similarity, calculate_similarity(t1, t2))

                    try:
                        year_i = int(art_i.get("publication_year", 0) or 0)
                        year_j = int(art_j.get("publication_year", 0) or 0)
                        year_close = abs(year_i - year_j) <= year_tolerance if year_i and year_j else False
                    except (ValueError, TypeError):
                        year_close = False

                    if best_similarity >= min_similarity and year_close:
                        uf.union(idx_i, idx_j)

    def _is_deduplicable_scielo_pair(self, left_doc, right_doc):
        left_type = extract_scielo_document_type(left_doc)
        right_type = extract_scielo_document_type(right_doc)
        if not left_type or not right_type or left_type != right_type:
            return False

        allowed_types = set(self.rules.get("scielo_dedup_allowed_types") or [])
        if left_type not in allowed_types:
            return False

        return normalize_document_type_for_etl(left_type) == self.rules["document_type"]

    def _has_matching_publication_year(self, left_doc, right_doc):
        try:
            year_left = int(left_doc.get("publication_year", 0) or 0)
            year_right = int(right_doc.get("publication_year", 0) or 0)

        except (ValueError, TypeError):
            return False

        return year_left == year_right and year_left > 0

    def _has_matching_source(self, left_doc, right_doc):
        issns_left = set(extract_issns(left_doc))
        issns_right = set(extract_issns(right_doc))
        if issns_left & issns_right:
            return True

        return bool(
            left_doc.get("journal_title") == right_doc.get("journal_title")
            and left_doc.get("journal_title")
        )

    def _has_overlapping_title(self, left_doc, right_doc):
        return bool(set(extract_titles(left_doc)) & set(extract_titles(right_doc)))

    def _has_required_context_match(self, left_doc, right_doc, prefix):
        if (
            self.rules.get(f"{prefix}_requires_year_match", False)
            and not self._has_matching_publication_year(left_doc, right_doc)
        ):
            return False

        if (
            self.rules.get(f"{prefix}_requires_source_match", False)
            and not self._has_matching_source(left_doc, right_doc)
        ):
            return False

        if (
            self.rules.get(f"{prefix}_requires_title_overlap", False)
            and not self._has_overlapping_title(left_doc, right_doc)
        ):
            return False

        return True
