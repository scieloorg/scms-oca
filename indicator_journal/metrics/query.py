from typing import Any, Dict

from indicator.metrics.engine import MetricEngine
from .normalizers import normalize_int


class JournalMetricQuery:
    def __init__(self, data_source: Any):
        self.data_source = data_source

    def build_global_ranking_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        ranking_field = self.data_source.get_index_field_name(params["ranking_metric"]) or params["ranking_metric"]
        journal_id_field = self.data_source.get_index_field_name("journal_id") or "journal_id"

        year_field = self.data_source.get_index_field_name("publication_year")
        must_clauses = [{"term": {year_field: params["publication_year"]}}]
        for form_key, val in params["filters"].items():
            field = self.data_source.get_field(form_key)
            index_field_name = field.index_field_name if field else form_key
            is_bool = field and (field.transform_config.get("type") == "boolean" or field.display_transform == "boolean")

            if is_bool:
                if val in ("true", "false", True, False):
                    must_clauses.append({"term": {index_field_name: val in ("true", True)}})
            elif isinstance(val, (list, tuple)):
                must_clauses.append({"terms": {index_field_name: list(val)}})
            else:
                must_clauses.append({"term": {index_field_name: val}})

        return {
            "size": params["limit"],
            "track_total_hits": True,
            "query": {"bool": {"must": must_clauses}},
            "sort": [{ranking_field: {"order": "desc", "missing": "_last", "unmapped_type": "float"}}],
            "collapse": {"field": journal_id_field},
        }

    def build_thematic_ranking_query(
        self,
        publication_year: Any,
        ranking_metric: str,
        limit: int,
        minimum_publications: int,
        cleaned_filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        query = MetricEngine(self.data_source, filters={}).build_filter_query(cleaned_filters)

        must = []
        must_not = []
        if query and "bool" in query:
            must.extend(query["bool"].get("must", []))
            must_not.extend(query["bool"].get("must_not", []))

        if publication_year not in (None, ""):
            must.append({
                "term": {
                    self.data_source.get_index_field_name("publication_year"): normalize_int(publication_year, publication_year)
                }
            })

        if minimum_publications is not None:
            must.append({"range": {self.data_source.get_index_field_name("journal_publications_count"): {"gte": minimum_publications}}})

        thematic_query = {"bool": {"must": must, "must_not": must_not}} if must or must_not else {"match_all": {}}
        ranking_field = self.data_source.get_index_field_name(ranking_metric) or ranking_metric
        journal_id_field = self.data_source.get_index_field_name("journal_id") or "journal_id"

        return {
            "query": thematic_query,
            "size": limit,
            "track_total_hits": True,
            "sort": [{ranking_field: {"order": "desc", "missing": "_last", "unmapped_type": "float"}}],
            "collapse": {"field": journal_id_field},
            "aggs": {
                "unique_journals": {"cardinality": {"field": journal_id_field}}
            },
        }
