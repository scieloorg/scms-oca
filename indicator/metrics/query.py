from typing import Any, Dict
from indicator import filters as indicator_filters
from .config import MetricGroup


class MetricQuery:
    def __init__(self, data_source: Any, metric_group: MetricGroup):
        self.data_source = data_source
        self.metric_group = metric_group

    def build_query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        filters = dict(filters or {})

        field_settings = self.data_source.get_field_settings_dict()
        translated_filters = indicator_filters.translate_filter_fields(filters, field_settings)

        query_config = self.data_source.metric_config_schema.get("query") or {}
        must = list(query_config.get("must") or [])
        must_not = list(query_config.get("must_not") or [])

        query_operator_fields = {
            field_name: cfg.get("index_field_name")
            for field_name, cfg in field_settings.items()
            if cfg.get("settings", {}).get("support_query_operator") and cfg.get("index_field_name")
        }
        index_field_name_to_filter_name_map = {
            cfg.get("index_field_name"): field_name
            for field_name, cfg in field_settings.items()
            if cfg.get("index_field_name")
        }

        for index_field_name, value in translated_filters.items():
            filter_name = index_field_name_to_filter_name_map.get(index_field_name)
            if not filter_name:
                continue

            is_not = filters.get(f"{filter_name}_bool_not") == "true"

            if isinstance(value, list):
                self._add_list(filters, filter_name, index_field_name, query_operator_fields, value, must)
            elif isinstance(value, dict):
                if is_not:
                    must_not.append({"range": {index_field_name: value}})
                else:
                    must.append({"range": {index_field_name: value}})
            else:
                if is_not:
                    self._add_term(index_field_name, value, must_not)
                else:
                    self._add_term(index_field_name, value, must)

        query_bool = {}
        if must:
            query_bool["must"] = must
        if must_not:
            query_bool["must_not"] = must_not

        return {"bool": query_bool} if query_bool else {"match_all": {}}

    def _add_list(self, filters, filter_name, qualified_index_field_name, query_operator_fields, values, must):
        normalized_values = indicator_filters.normalize_filter_values(values)
        if not normalized_values:
            return

        operator_value = filters.get(f"{filter_name}_operator")
        if operator_value == "and" and filter_name in query_operator_fields:
            for value in normalized_values:
                self._add_term(qualified_index_field_name, value, must)
        else:
            must.append({"terms": {qualified_index_field_name: normalized_values}})

    def _add_term(self, name, value, must):
        if value in (None, ""):
            return
        must.append({"term": {name: value}})

    def build_aggs(self) -> Dict[str, Any]:
        time_dim = self.metric_group.time_dimension
        time_field = self.data_source.get_index_field_name(time_dim.get("field", "publication_year"))
        agg_type = time_dim.get("agg_type", "terms")

        if agg_type == "date_histogram":
            per_time = {
                "date_histogram": {
                    "field": time_field,
                    "calendar_interval": time_dim.get("calendar_interval", "year"),
                    "format": time_dim.get("format", "yyyy"),
                    "min_doc_count": 1,
                },
                "aggs": {},
            }
        else:
            per_time = {
                "terms": {
                    "field": time_field,
                    "order": {"_key": "asc"},
                    "size": 1000,
                },
                "aggs": {},
            }

        child_aggs = {}
        for metric in self.metric_group.physical_metrics:
            if metric.agg == "count":
                continue

            if metric.agg in ("sum", "avg", "cardinality", "min", "max"):
                physical_field = self.data_source.get_index_field_name(metric.field)
                child_aggs[metric.key] = {
                    metric.agg: {"field": physical_field}
                }
            elif metric.agg == "filter" and metric.filter_query:
                sub_aggs = self._build_sub_aggs(metric.sub_aggs)
                child_aggs[metric.key] = {
                    "filter": metric.filter_query,
                    **({"aggs": sub_aggs} if sub_aggs else {})
                }

        per_time["aggs"] = dict(child_aggs)

        if self.metric_group.breakdown_variable:
            breakdown_field = self.data_source.get_index_field_name(self.metric_group.breakdown_variable)
            per_time["aggs"]["breakdown"] = {
                "terms": {
                    "field": breakdown_field,
                    "order": {"_key": "asc"},
                    "size": 2500,
                },
                "aggs": dict(child_aggs),
            }

        return {"per_year": per_time}

    def _build_sub_aggs(self, raw_sub_aggs):
        sub_aggs = {}
        for sub_key, sub_val in (raw_sub_aggs or {}).items():
            sub_agg_type = list(sub_val.keys())[0]
            sub_field = sub_val[sub_agg_type].get("field")
            physical_sub_field = self.data_source.get_index_field_name(sub_field)
            sub_aggs[sub_key] = {
                sub_agg_type: {"field": physical_sub_field}
            }
        return sub_aggs
