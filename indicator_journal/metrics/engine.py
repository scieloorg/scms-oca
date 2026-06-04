from typing import Any, Dict, List, Tuple

from search_gateway.client import get_opensearch_client
from search_gateway.models import DataSource
from indicator.filters import clean_filters
from indicator.metrics.engine import MetricEngine
from .normalizers import normalize_int, normalize_float, normalize_option
from .query import JournalMetricQuery
from .result import JournalMetricResultBuilder
from .presentation import JournalMetricPresentation
from .config import JournalMetricConfig


class JournalMetricEngine:
    def __init__(self, data_source: Any):
        self.data_source = data_source
        self.config = JournalMetricConfig(data_source)
        self.query_builder = JournalMetricQuery(data_source)
        self.result_builder = JournalMetricResultBuilder(data_source)
        self.presentation = JournalMetricPresentation(data_source)

    def get_field_default(self, field_name: str, fallback: Any = None) -> Any:
        field = self.data_source.get_field(field_name)
        if not field:
            return fallback
        val = field.default_value
        return fallback if val in (None, "", [], {}) else val

    def get_required_field_default(self, field_name: str) -> Any:
        value = self.get_field_default(field_name)
        if value in (None, "", [], {}):
            raise ValueError(f"Missing default value for journal metric field '{field_name}'")
        return value

    def get_field_options(self, field_name: str, lower: bool = False) -> List[str]:
        field = self.data_source.get_field(field_name)
        if not field:
            return []
        opts = [str(opt.get("value") or "").strip() for opt in field.static_options if opt.get("value")]
        return [o.lower() for o in opts] if lower else opts

    def _bool_query(self, must_clauses: List[Dict[str, Any]], must_not_clauses: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        bool_part = {"must": list(must_clauses)}
        if must_not_clauses:
            bool_part["must_not"] = must_not_clauses
        return {"bool": bool_part}

    def _strip_term_clause(self, clauses: List[Dict[str, Any]], field_name: str) -> List[Dict[str, Any]]:
        return [
            clause
            for clause in (clauses or [])
            if not (
                isinstance(clause, dict)
                and isinstance(clause.get("term"), dict)
                and field_name in clause.get("term", {})
            )
        ]

    def normalize_global_request_filters(self, request_filters: Any) -> Dict[str, Any]:
        global_form_key = self.config.form_key("global")
        default_year = self.get_required_field_default("publication_year")
        default_metric = self.get_required_field_default("ranking_metric")
        default_limit = normalize_int(self.get_required_field_default("limit"))

        year = request_filters.get("publication_year") or default_year
        metric = request_filters.get("ranking_metric") or default_metric
        limit = normalize_int(request_filters.get("limit")) or default_limit

        fields = self.data_source.get_ordered_fields(form_key=global_form_key)
        extra_keys = {field.field_name for field in fields} - {"ranking_metric", "limit", "publication_year"}

        filters = {}
        for form_key in extra_keys:
            val = request_filters.getlist(form_key) if hasattr(request_filters, "getlist") else request_filters.get(form_key)

            if isinstance(val, list):
                val = [v for v in val if v not in (None, "")]
                if not val:
                    val = None
                elif len(val) == 1:
                    val = val[0]
            elif val in (None, ""):
                val = None

            if val not in (None, "", [], ()):
                filters[form_key] = val

        return {
            "publication_year": year,
            "ranking_metric": metric,
            "limit": limit,
            "filters": filters,
        }

    def get_global_ranking(self, request_filters: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        params = self.normalize_global_request_filters(request_filters)

        es = get_opensearch_client()
        body = self.query_builder.build_global_ranking_query(params)

        try:
            response = es.search(index=self.data_source.index_name, body=body)
        except Exception:
            response = {}

        hits = response.get("hits", {}).get("hits", [])
        journals = [self.result_builder.parse_hit(hit) for hit in hits]

        applied_filters = {
            "publication_year": params["publication_year"],
            "ranking_metric": params["ranking_metric"],
            "limit": str(params["limit"]),
            **params["filters"],
        }

        ranking_data = {
            "ranking_metric": params["ranking_metric"],
            "year": params["publication_year"],
            "journals": journals,
        }

        return ranking_data, applied_filters

    def get_thematic_ranking(self, form_filters: Dict[str, Any]) -> Tuple[Dict[str, Any] or None, str or None]:
        es = get_opensearch_client()

        payload_filters = dict(form_filters)
        category_levels = self.get_field_options("category_level", lower=True)
        default_cat_level = self.get_required_field_default("category_level")
        default_cat_id = self.get_field_default("category_id")
        default_ranking = self.get_required_field_default("ranking_metric")
        default_limit = normalize_int(self.get_required_field_default("limit"))
        default_min_pubs = normalize_int(self.get_required_field_default("minimum_publications"))

        has_explicit_category_level = str(payload_filters.get("category_level") or "").strip() != ""
        has_explicit_category_id = str(payload_filters.get("category_id") or "").strip() != ""

        payload_filters["category_level"] = normalize_option(
            payload_filters.get("category_level"), category_levels, default_cat_level, lower=True
        )
        if not has_explicit_category_level and not has_explicit_category_id:
            payload_filters["category_id"] = default_cat_id

        publication_year = (
            payload_filters.pop("publication_year", None)
            or payload_filters.pop("year", None)
            or self.get_field_default("publication_year")
        )
        ranking_metric = normalize_option(
            payload_filters.pop("ranking_metric", None),
            self.get_field_options("ranking_metric"),
            default_ranking,
        )
        limit = normalize_int(payload_filters.pop("limit", None)) or default_limit
        limit = max(1, min(limit, 5000))
        minimum_publications = normalize_int(payload_filters.pop("minimum_publications", None)) or default_min_pubs

        cleaned_filters = clean_filters(payload_filters)
        body = self.query_builder.build_thematic_ranking_query(
            publication_year=publication_year,
            ranking_metric=ranking_metric,
            limit=limit,
            minimum_publications=minimum_publications,
            cleaned_filters=cleaned_filters,
        )

        try:
            response = es.search(index=self.data_source.index_name, body=body)
            hits = response.get("hits", {}).get("hits", [])

            journals = [self.result_builder.parse_hit(hit) for hit in hits]
            journals.sort(key=lambda item: normalize_float(item.get(ranking_metric)) or 0.0, reverse=True)

            unique_journals = int(response.get("aggregations", {}).get("unique_journals", {}).get("value", len(journals)))

            return {
                "journals": journals,
                "total_journals": unique_journals,
                "returned_journals": len(journals),
                "year": publication_year,
                "ranking_metric": ranking_metric,
            }, None

        except Exception as exc:
            return None, f"Error executing search: {exc}"

    def get_profile_timeseries(
        self,
        issn: str,
        category_id: str = None,
        category_level: str = None,
        publication_year: str = None,
        form_filters: Dict[str, Any] = None,
    ) -> Tuple[Dict[str, Any] or None, str or None]:
        if not issn:
            return None, "Missing journal identifier"

        es = get_opensearch_client()

        category_levels = self.get_field_options("category_level", lower=True)
        default_cat_level = self.get_required_field_default("category_level")
        selected_category_level = normalize_option(category_level, category_levels, default_cat_level, lower=True)

        cleaned_filters = clean_filters(dict(form_filters or {}))
        control_filter_keys = (
            MetricEngine.REQUEST_CONTROL_FILTER_KEYS
            | set(self.data_source.get_form_control_field_names(self.config.form_key("thematic")))
        )
        for key in control_filter_keys | {"publication_year", "year", "journal_title", "journal_issn", "category_id", "category_level"}:
            cleaned_filters.pop(key, None)

        cleaned_filters["category_level"] = selected_category_level
        inherited_must, inherited_must_not = MetricEngine(self.data_source, filters={}).build_filter_clauses(cleaned_filters)
        inherited_must = self._strip_term_clause(inherited_must, self.data_source.get_index_field_name("category_level"))

        base_must = list(inherited_must)
        if str(issn).startswith("http"):
            base_must.append({"term": {self.data_source.get_index_field_name("journal_id"): issn}})
        else:
            base_must.append({"term": {self.data_source.get_index_field_name("journal_issn"): issn}})

        index_name = self.data_source.index_name

        levels_body = {
            "size": 0,
            "query": self._bool_query(base_must, inherited_must_not),
            "aggs": {
                "category_levels": {
                    "terms": {
                        "field": self.data_source.get_index_field_name("category_level"),
                        "size": len(category_levels) or 10,
                    }
                }
            },
        }

        available_category_levels = []
        try:
            levels_res = es.search(index=index_name, body=levels_body)
            buckets = levels_res.get("aggregations", {}).get("category_levels", {}).get("buckets", [])
            for b in buckets:
                lvl = str(b.get("key") or "").strip().lower()
                if lvl in category_levels and lvl not in available_category_levels:
                    available_category_levels.append(lvl)
        except Exception:
            pass

        if available_category_levels and selected_category_level not in available_category_levels:
            selected_category_level = available_category_levels[0]

        categories_must = list(base_must) + [
            {"term": {self.data_source.get_index_field_name("category_level"): selected_category_level}}
        ]
        if publication_year not in (None, ""):
            categories_must.append({"term": {"publication_year": normalize_int(publication_year, publication_year)}})

        categories_body = {
            "size": 0,
            "query": self._bool_query(categories_must, inherited_must_not),
            "aggs": {
                "categories": {
                    "terms": {
                        "field": self.data_source.get_index_field_name("category_id"),
                        "size": 2000,
                        "order": {"publications_total": "desc"},
                    },
                    "aggs": {
                        "publications_total": {"sum": {"field": self.data_source.get_index_field_name("journal_publications_count")}},
                    },
                }
            },
        }

        available_categories = []
        try:
            categories_res = es.search(index=index_name, body=categories_body)
            buckets = categories_res.get("aggregations", {}).get("categories", {}).get("buckets", [])
            available_categories = [str(b.get("key")).strip() for b in buckets if b.get("key")]
        except Exception:
            pass

        selected_category_id = str(category_id).strip() if category_id not in (None, "") else None
        if selected_category_id and selected_category_id not in available_categories:
            selected_category_id = None
        if not selected_category_id and available_categories:
            selected_category_id = available_categories[0]

        data_must = list(base_must) + [
            {"term": {self.data_source.get_index_field_name("category_level"): selected_category_level}}
        ]
        if selected_category_id:
            data_must.append({"term": {self.data_source.get_index_field_name("category_id"): selected_category_id}})

        hits_body = {
            "size": 1000,
            "query": self._bool_query(data_must, inherited_must_not),
            "sort": [
                {"publication_year": {"order": "asc"}},
                {self.data_source.get_index_field_name("journal_impact_cohort"): {"order": "desc", "missing": "_last"}},
            ],
            "collapse": {"field": "publication_year"},
        }

        try:
            hits_res = es.search(index=index_name, body=hits_body)
            hits = hits_res.get("hits", {}).get("hits", [])
        except Exception as exc:
            return None, f"Error executing hits search: {exc}"

        if not hits:
            return None, "Not found"

        adapted_data, data = MetricEngine(self.data_source, filters={}).build_data_from_hits(
            group_key="thematic_profile",
            hits=hits,
            relative_metrics=None,
        )

        spider_must = list(base_must) + [
            {"term": {self.data_source.get_index_field_name("category_level"): selected_category_level}}
        ]
        if publication_year not in (None, ""):
            spider_must.append({"term": {"publication_year": normalize_int(publication_year, publication_year)}})

        spider_body = {
            "size": 0,
            "query": self._bool_query(spider_must, inherited_must_not),
            "aggs": {
                "by_category": {
                    "terms": {
                        "field": self.data_source.get_index_field_name("category_id"),
                        "size": 2000,
                    },
                    "aggs": {
                        "publications_total": {"sum": {"field": self.data_source.get_index_field_name("journal_publications_count")}},
                        "citations_total": {"sum": {"field": self.data_source.get_index_field_name("journal_citations_total")}},
                        "citations_mean": {"avg": {"field": self.data_source.get_index_field_name("journal_citations_mean")}},
                    },
                }
            },
        }

        category_spider = []
        try:
            spider_res = es.search(index=index_name, body=spider_body)
            buckets = spider_res.get("aggregations", {}).get("by_category", {}).get("buckets", [])
            for b in buckets:
                cat = b.get("key")
                if cat:
                    category_spider.append({
                        "category": cat,
                        "publications_total": normalize_int((b.get("publications_total") or {}).get("value")),
                        "citations_total": normalize_int((b.get("citations_total") or {}).get("value")),
                        "citations_mean": normalize_float((b.get("citations_mean") or {}).get("value")),
                    })
            category_spider.sort(key=lambda x: x.get("publications_total") or 0, reverse=True)
            category_spider = category_spider[:12]
        except Exception:
            pass

        snapshots = sorted([self.result_builder.parse_hit(hit) for hit in hits], key=lambda x: x["publication_year"] or 0)
        years = [str(item["publication_year"]) for item in snapshots]
        latest = snapshots[-1] if snapshots else {}
        first_source = hits[0].get("_source", {})

        profile_identity = {
            "journal_title": self.result_builder.get_nested_value(first_source, self.data_source.get_index_field_name("journal_title")),
            "journal_issn": self.result_builder.get_nested_value(first_source, self.data_source.get_index_field_name("journal_issn")),
            "journal_id": self.result_builder.get_nested_value(first_source, self.data_source.get_index_field_name("journal_id")),
            "publisher_name": latest.get("publisher_name"),
            "country": latest.get("country"),
            "collection": latest.get("collection"),
            "collection_name": latest.get("collection_name"),
            "collection_acronym": latest.get("collection_acronym"),
            "years": years,
            "latest_year": latest.get("publication_year"),
            "latest_year_metrics": latest,
            "annual_snapshots": snapshots,
        }

        numeric_field_names = {
            field.field_name
            for field in self.data_source.get_ordered_fields()
            if (
                field.widget_name in ("number", "year", "float")
                or field.field_name.endswith(("_pct", "_count", "_total", "_mean"))
                or "cohort" in field.field_name
            )
        }
        for field_name in numeric_field_names:
            profile_identity[f"{field_name}_per_year"] = [item.get(field_name) for item in snapshots]

        result_data = {
            **profile_identity,
            "years": adapted_data.get("years"),
            "charts": adapted_data.get("charts"),
            "available_categories": available_categories,
            "available_category_levels": available_category_levels or [selected_category_level],
            "selected_category_id": selected_category_id,
            "selected_category_level": selected_category_level,
            "category_publications_spider": category_spider,
        }

        for metric_key, values in data.get("metrics", {}).items():
            result_data[f"{metric_key}_per_year"] = values

        return result_data, None

    def resolve_journal_identity(self, es: Any, issn: str, profile_data: Dict[str, Any] = None) -> Dict[str, Any]:
        profile_data = profile_data or {}
        journal_id = str(profile_data.get("journal_id") or "").strip()

        if journal_id:
            return {
                "journal_id": journal_id,
                "journal_title": profile_data.get("journal_title"),
                "journal_issn": issn if not str(issn).startswith("http") else profile_data.get("journal_issn"),
                "country": profile_data.get("country"),
                "publisher_name": profile_data.get("publisher_name"),
            }

        match_field = (
            self.data_source.get_index_field_name("journal_id")
            if str(issn).startswith("http")
            else self.data_source.get_index_field_name("journal_issn")
        )
        year_field = self.data_source.get_index_field_name("publication_year")

        try:
            resp = es.search(
                index=self.data_source.index_name,
                body={
                    "query": {"term": {match_field: issn}},
                    "sort": [{year_field: {"order": "desc"}}],
                    "size": 1,
                },
            )
        except Exception:
            return {}

        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            return {}

        return self.result_builder.resolve_journal_identity(hits[0].get("_source") or {}, issn)

    def fetch_global_snapshot(self, issn: str, profile_data: Dict[str, Any] = None) -> Dict[str, Any] or None:
        global_ds = DataSource.get_by_index_name(index_name=self.config.related_global_data_source())
        if not global_ds:
            return None

        es = get_opensearch_client()
        if not es:
            return None

        journal_identity = self.resolve_journal_identity(es, issn, profile_data=profile_data)
        journal_id = str((journal_identity or {}).get("journal_id") or "").strip()
        if not journal_id:
            return None

        match_field = global_ds.get_index_field_name("journal_id")
        year_field = global_ds.get_index_field_name("publication_year")

        try:
            resp = es.search(
                index=global_ds.index_name,
                body={
                    "query": {"term": {match_field: journal_id}},
                    "sort": [{year_field: {"order": "desc"}}],
                    "size": 1000,
                },
            )
        except Exception:
            return None

        hits = resp.get("hits", {}).get("hits", [])
        sources = [
            self.result_builder.normalize_global_source(
                hit.get("_source") or {},
                global_ds,
                journal_issn=issn,
                journal_identity=journal_identity,
            )
            for hit in hits
        ]
        sources = [s for s in sources if s]
        if not sources:
            return None

        sources.sort(key=lambda s: s.get("publication_year") or 0)
        latest = dict(sources[-1])
        latest["_all_sources"] = sources
        return latest
