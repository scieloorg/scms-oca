from typing import Any, Dict, List

import sympy
from sympy.parsing.sympy_parser import parse_expr

from .config import MetricGroup


class MetricResultBuilder:
    def __init__(self, data_source: Any, metric_group: MetricGroup):
        self.data_source = data_source
        self.metric_group = metric_group

    def build_from_response(self, es_response: Dict[str, Any]) -> Dict[str, Any]:
        data = self._parse_response(es_response)
        return self.compute_metrics(data)

    def build_from_hits(self, hits) -> Dict[str, Any]:
        buckets = self._build_buckets_from_hits(hits)
        response = {"aggregations": {"per_year": {"buckets": buckets}}}
        return self.build_from_response(response)

    def compute_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        years = data.get("years", [])
        if not years:
            return data

        if "series" not in data:
            metrics_data = data.get("metrics", {})
            for comp_metric in self.metric_group.computed_metrics:
                computed_series = []
                for idx in range(len(years)):
                    context = {}
                    for phys_key, vals in metrics_data.items():
                        if idx < len(vals):
                            context[phys_key] = vals[idx]

                    val = self._evaluate_formula(comp_metric.formula, context, comp_metric.precision)
                    computed_series.append(val)

                metrics_data[comp_metric.key] = computed_series
            return data

        series = data.get("series", [])
        breakdown_keys = data.get("breakdown_keys", [])

        new_series = list(series)
        for comp_metric in self.metric_group.computed_metrics:
            for breakdown in breakdown_keys:
                computed_values = []
                for idx in range(len(years)):
                    context = {}
                    for s in series:
                        if self._series_breakdown_name(s) == breakdown or s.get("name") == breakdown:
                            phys_key = s.get("metric_key")
                            if phys_key and idx < len(s.get("data", [])):
                                context[phys_key] = s["data"][idx]

                    val = self._evaluate_formula(comp_metric.formula, context, comp_metric.precision)
                    computed_values.append(val)

                new_series.append({
                    "name": f"{breakdown} ({comp_metric.get_label()})",
                    "data": computed_values,
                    "type": comp_metric.key,
                    "metric_key": comp_metric.key,
                })

        data["series"] = new_series
        return data

    def compute_relative_metrics(
        self,
        filtered_data: Dict[str, Any],
        baseline_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        years = filtered_data.get("years", [])
        baseline_years = baseline_data.get("years", [])

        if not years or not baseline_data:
            return {"enabled": False}

        relative_metrics = {
            "enabled": True,
        }

        if "series" not in filtered_data:
            filtered_metrics = filtered_data.get("metrics", {})
            baseline_metrics = baseline_data.get("metrics", {})

            for key in list(filtered_metrics.keys()):
                filtered_vals = filtered_metrics[key]
                baseline_vals = baseline_metrics.get(key) or []

                aligned_filtered = filtered_vals
                aligned_baseline = self._align_series_to_years(years, baseline_years, baseline_vals)

                relative_key = f"{key}_share_pct_per_year"
                relative_metrics[relative_key] = self._compute_relative_percent_series(
                    aligned_filtered,
                    aligned_baseline,
                )
            return relative_metrics

        filtered_series = filtered_data.get("series", [])
        baseline_series = baseline_data.get("series", [])

        relative_series = []
        for s in filtered_series:
            metric_key = s.get("metric_key")
            base_s = None
            for bs in baseline_series:
                if bs.get("metric_key") == metric_key or bs.get("type") == metric_key:
                    base_s = bs
                    break

            if not base_s:
                aligned_baseline = [0 for _ in years]
            else:
                aligned_baseline = self._align_series_to_years(years, baseline_years, base_s.get("data", []))

            rel_data = self._compute_relative_percent_series(s.get("data", []), aligned_baseline)
            relative_series.append({
                "name": s.get("name"),
                "data": rel_data,
                "type": s.get("type"),
                "metric_key": metric_key,
            })

        relative_metrics["series"] = relative_series
        return relative_metrics

    def _parse_response(self, es_response: Dict[str, Any]) -> Dict[str, Any]:
        aggs = es_response.get("aggregations", {})
        per_year_buckets = aggs.get("per_year", {}).get("buckets", [])

        years = [
            str(b.get("key_as_string") or b.get("key"))
            for b in per_year_buckets
        ]

        data = {
            "years": years,
            "metrics": {},
        }

        if not self.metric_group.breakdown_variable:
            for metric in self.metric_group.physical_metrics:
                data["metrics"][metric.key] = [
                    self._extract_metric_value(b, metric)
                    for b in per_year_buckets
                ]
            return data

        data["breakdown_variable"] = self.metric_group.breakdown_variable

        breakdown_keys_set = set()
        for year_bucket in per_year_buckets:
            for b in year_bucket.get("breakdown", {}).get("buckets", []):
                breakdown_keys_set.add(str(b["key"]))

        breakdown_keys = sorted(list(breakdown_keys_set))
        series = []

        for breakdown in breakdown_keys:
            for metric in self.metric_group.physical_metrics:
                metric_values = []
                for year_bucket in per_year_buckets:
                    found_bucket = None
                    for b in year_bucket.get("breakdown", {}).get("buckets", []):
                        if str(b["key"]) == breakdown:
                            found_bucket = b
                            break

                    if found_bucket is None:
                        metric_values.append(0)
                    else:
                        metric_values.append(self._extract_metric_value(found_bucket, metric))

                series.append({
                    "name": breakdown,
                    "data": metric_values,
                    "type": metric.key,
                })

        standardized_breakdown_keys = _standardize_breakdown_keys(
            breakdown_keys,
            series,
            data_source=self.data_source,
            breakdown_variable=self.metric_group.breakdown_variable,
        )

        for s in series:
            metric_key = s.get("type")
            metric_def = self.metric_group.get_metric(metric_key)
            metric_label = metric_def.get_label() if metric_def else metric_key
            s["name"] = f"{s['name']} ({metric_label})"
            s["metric_key"] = metric_key

        data["breakdown_keys"] = standardized_breakdown_keys
        data["series"] = series

        return data

    def _extract_metric_value(self, bucket: Dict[str, Any], metric: Any) -> Any:
        if metric.agg == "count" or not metric.field:
            return bucket.get("doc_count", 0)

        if metric.path:
            val = _get_nested_value(bucket, metric.path)
            return self._normalize_number(val)

        if metric.agg == "filter":
            val = bucket.get(metric.key, {}).get("doc_count")
            if val is not None:
                return self._normalize_number(val)

        agg_bucket = bucket.get(metric.key) or {}
        if isinstance(agg_bucket, dict):
            val = agg_bucket.get("value")
            if val is not None:
                return self._normalize_number(val)

        return 0

    def _evaluate_formula(self, formula_str: str, context: Dict[str, Any], precision: int) -> float:
        try:
            expr = parse_expr(str(formula_str).strip())
            safe_context = {}
            for sym in expr.free_symbols:
                safe_context[sym] = context.get(str(sym), 0)

            substituted = expr.subs(safe_context)
            result = substituted.evalf()

            if result in (sympy.nan, sympy.oo, sympy.zoo, -sympy.oo) or not result.is_number:
                return 0.0

            val = float(result)
            return round(val, precision)
        except Exception:
            return 0.0

    def _series_breakdown_name(self, series: Dict[str, Any]) -> str:
        name = series.get("name", "")
        metric = self.metric_group.get_metric(series.get("metric_key"))
        if not metric:
            return name
        return name.replace(f" ({metric.get_label()})", "")

    def _align_series_to_years(
        self,
        reference_years: List[str],
        source_years: List[str],
        source_values: List[Any],
    ) -> List[Any]:
        if not reference_years:
            return []
        if not source_years or not source_values:
            return [0 for _ in reference_years]

        values_by_year = {}
        for idx, year in enumerate(source_years):
            if idx >= len(source_values):
                continue
            values_by_year[str(year)] = source_values[idx]

        return [values_by_year.get(str(year), 0) for year in reference_years]

    def _compute_relative_percent_series(
        self,
        filtered_values: List[Any],
        baseline_values: List[Any],
        precision: int = 2,
    ) -> List[float]:
        relative_values = []
        for filtered_val, baseline_val in zip(filtered_values, baseline_values):
            try:
                filtered_num = float(filtered_val)
            except (TypeError, ValueError):
                filtered_num = 0.0
            try:
                baseline_num = float(baseline_val)
            except (TypeError, ValueError):
                baseline_num = 0.0

            if baseline_num <= 0:
                relative_values.append(0.0)
                continue

            relative_values.append(round((filtered_num / baseline_num) * 100, precision))

        return relative_values

    def _normalize_number(self, value: Any) -> Any:
        if value is None:
            return 0
        try:
            if isinstance(value, float):
                if value.is_integer():
                    return int(value)
                return value
            return int(value)
        except (TypeError, ValueError):
            return value

    def _build_buckets_from_hits(self, hits):
        buckets = []
        for hit in hits:
            source_data = hit.get("_source") or {}
            bucket = {
                "key": source_data.get("publication_year"),
                "key_as_string": str(source_data.get("publication_year")),
                "doc_count": 1,
            }
            for metric in self.metric_group.physical_metrics:
                physical_field = self.data_source.get_index_field_name(metric.field)
                val = _get_nested_value(source_data, physical_field)
                if val is not None:
                    bucket[metric.key] = {"value": val}
            buckets.append(bucket)
        return buckets


def _standardize_breakdown_keys(keys, series, data_source=None, breakdown_variable=None):
    if data_source and breakdown_variable:
        field = data_source.get_field(breakdown_variable)
        if field and field.static_options:
            mapping = {
                str(opt.get("value")): str(opt.get("label"))
                for opt in field.static_options
                if "value" in opt and "label" in opt
            }
            if any(str(k) in mapping for k in keys):
                return _apply_mapping(keys, series, mapping)

    return keys


def _apply_mapping(keys, series, mapping):
    for s in series:
        s["name"] = mapping.get(str(s["name"]), s["name"])
    return [mapping.get(str(k), k) for k in keys]


def _get_nested_value(data, key, default=None):
    if not isinstance(data, dict) or not key:
        return default

    current = data
    for part in str(key).split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current
