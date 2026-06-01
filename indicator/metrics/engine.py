from typing import Any, Dict

from .config import MetricGroup
from .presentation import MetricPresentation
from .query import MetricQuery
from .result import MetricResultBuilder


class MetricEngine:
    REQUEST_CONTROL_FILTER_KEYS = {
        "breakdown_variable",
        "study_unit",
        "return_study_unit",
        "csrfmiddlewaretoken",
    }
    SOURCE_STUDY_UNIT_ALIASES = {"source", "journal"}

    def __init__(self, data_source: Any, filters: Dict[str, Any], study_unit: str = "document"):
        self.data_source = data_source
        self.filters = filters or {}
        self.study_unit = study_unit
        self.group_key, self.group_config = self._resolve_group_config(study_unit)

    def run(self, es):
        if not self.group_config:
            return None, f"Study unit '{self.group_key}' not found in metric_config"

        metric_group = self._build_metric_group(breakdown_variable=self.filters.get("breakdown_variable"))
        data, error = self._fetch_metric_data(es, metric_group, self.filters)
        if error:
            return None, error

        relative_metrics = self._build_relative_metrics(es, metric_group, data)
        adapted_data = MetricPresentation(self.data_source, metric_group).adapt_data(data, relative_metrics)
        adapted_data["study_unit"] = self.study_unit
        adapted_data["data_source"] = self.data_source.index_name

        return adapted_data, None

    def build_filter_query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        metric_group = MetricGroup("_filter", {}, [])
        return MetricQuery(self.data_source, metric_group).build_query(filters)

    def build_filter_clauses(self, filters: Dict[str, Any]):
        query = self.build_filter_query(filters)
        if isinstance(query, dict) and "bool" in query:
            bool_query = query.get("bool") or {}
            return list(bool_query.get("must", [])), list(bool_query.get("must_not", []))
        return [], []

    def build_data_from_hits(
        self,
        group_key: str,
        hits,
        breakdown_variable=None,
        relative_metrics=None,
    ):
        metric_group = self._build_group_from_config(
            group_key,
            breakdown_variable=breakdown_variable,
        )
        data = MetricResultBuilder(self.data_source, metric_group).build_from_hits(hits)
        adapted_data = MetricPresentation(self.data_source, metric_group).adapt_data(
            data,
            relative_metrics=relative_metrics,
        )
        return adapted_data, data

    def _resolve_group_config(self, study_unit):
        raw_unit = str(study_unit or "").strip().lower()
        group_key = "source" if raw_unit in self.SOURCE_STUDY_UNIT_ALIASES else "document"
        study_units = self.data_source.metric_config_schema.get("study_units") or {}

        if group_key not in study_units and study_units:
            group_key = list(study_units.keys())[0]

        return group_key, study_units.get(group_key) or {}

    def _build_metric_group(self, breakdown_variable=None):
        return MetricGroup.from_config(
            group_key=self.group_key,
            group_dict=self.group_config,
            breakdown_variable=breakdown_variable,
        )

    def _build_group_from_config(self, group_key, breakdown_variable=None):
        study_units = self.data_source.metric_config_schema.get("study_units") or {}
        resolved_group_key = group_key
        if resolved_group_key not in study_units and study_units:
            resolved_group_key = list(study_units.keys())[0]

        return MetricGroup.from_config(
            group_key=resolved_group_key,
            group_dict=study_units.get(resolved_group_key) or {},
            breakdown_variable=breakdown_variable,
        )

    def _fetch_metric_data(self, es, metric_group, filters):
        metric_query = MetricQuery(self.data_source, metric_group)
        body = {
            "size": 0,
            "query": metric_query.build_query(filters),
            "aggs": metric_query.build_aggs(),
        }

        try:
            response = es.search(index=self.data_source.index_name, body=body)
        except Exception as exc:
            return None, f"Error executing search: {exc}"

        data = MetricResultBuilder(self.data_source, metric_group).build_from_response(response)
        return data, None

    def _build_relative_metrics(self, es, metric_group, data):
        control_filter_keys = self._build_indicator_control_filter_keys()
        baseline_filters, comparative_filter_keys = self._build_comparison_baseline_filters(
            control_filter_keys=control_filter_keys,
        )
        compared_filters = sorted(comparative_filter_keys)
        relative_metrics = {
            "enabled": False,
            "compared_filters": compared_filters,
        }

        if not comparative_filter_keys:
            return relative_metrics

        baseline_group = self._build_metric_group(breakdown_variable=None)
        baseline_data, error = self._fetch_metric_data(es, baseline_group, baseline_filters)
        if error:
            return relative_metrics

        relative_metrics = MetricResultBuilder(self.data_source, metric_group).compute_relative_metrics(
            data,
            baseline_data,
        )
        relative_metrics["compared_filters"] = compared_filters
        return relative_metrics

    def _build_indicator_control_filter_keys(self):
        control_filter_keys = set(self.REQUEST_CONTROL_FILTER_KEYS)
        try:
            control_filter_keys.update(self.data_source.get_form_control_field_names("indicator"))
        except Exception:
            pass
        return control_filter_keys

    def _build_comparison_baseline_filters(self, control_filter_keys=None):
        if not isinstance(self.filters, dict):
            return {}, []

        control_filter_keys = set(control_filter_keys or self.REQUEST_CONTROL_FILTER_KEYS)
        baseline_filters = {}
        comparative_filter_keys = []

        for key, value in self.filters.items():
            if key in control_filter_keys:
                continue
            if key.endswith("_operator") or key.endswith("_bool_not"):
                continue
            if not self._has_filter_value(value):
                continue

            if key in self._baseline_preserved_filter_keys():
                baseline_filters[key] = value
                operator_key = f"{key}_operator"
                bool_not_key = f"{key}_bool_not"
                if self._has_filter_value(self.filters.get(operator_key)):
                    baseline_filters[operator_key] = self.filters.get(operator_key)
                if self._has_filter_value(self.filters.get(bool_not_key)):
                    baseline_filters[bool_not_key] = self.filters.get(bool_not_key)
                continue

            comparative_filter_keys.append(key)

        return baseline_filters, comparative_filter_keys

    def _has_filter_value(self, value):
        if isinstance(value, list):
            return any(str(item).strip() for item in value if item is not None)
        return str(value).strip() != ""

    def _baseline_preserved_filter_keys(self):
        comparison_config = self.data_source.metric_config_schema.get("comparison") or {}
        return set(comparison_config.get("preserve_filters") or [])
