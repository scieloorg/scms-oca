from typing import Any, Dict, Optional
from django.utils.translation import get_language
from search_gateway.transforms import apply_transform
from .config import ComputedMetric, MetricGroup, PhysicalMetric


class MetricPresentation:
    def __init__(self, data_source: Any, metric_group: MetricGroup):
        self.data_source = data_source
        self.metric_group = metric_group

    def adapt_data(
        self,
        computed_data: Dict[str, Any],
        relative_metrics: Dict[str, Any],
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not lang:
            lang = get_language() or "pt"

        displays = self.data_source.metric_config_schema.get("displays") or {}
        charts_config = displays.get("charts") or {}

        adapted_charts = []
        years = computed_data.get("years", [])
        has_breakdown = bool(computed_data.get("breakdown_variable"))

        chart_items = sorted(
            charts_config.items(),
            key=lambda item: (item[1].get("order", 999), item[0]),
        )
        for chart_id, cfg in chart_items:
            if has_breakdown and cfg.get("hide_when_breakdown"):
                continue

            chart_study_units = cfg.get("study_units")
            if isinstance(chart_study_units, str):
                chart_study_units = [chart_study_units]
            if chart_study_units and self.metric_group.key not in set(chart_study_units):
                continue

            metric_keys = cfg.get("metrics") or cfg.get("metric")
            if isinstance(metric_keys, str):
                metric_keys = [metric_keys]
            metric_keys = [key for key in (metric_keys or []) if key]
            metric_defs = [self.metric_group.get_metric(metric_key) for metric_key in metric_keys]
            metric_defs = [metric_def for metric_def in metric_defs if metric_def]
            if not metric_defs:
                continue

            chart_title_dict = cfg.get("title") or {}
            chart_title = chart_title_dict.get(lang) or chart_title_dict.get("pt") or metric_defs[0].get_label(lang)

            chart_series = []
            if not has_breakdown:
                for metric_def in metric_defs:
                    vals = computed_data.get("metrics", {}).get(metric_def.key) or []
                    chart_series.append({
                        "name": metric_def.get_label(lang),
                        "data": vals,
                        "type": cfg.get("type", "bar"),
                        **({"stack": cfg.get("stack")} if cfg.get("stack") else {}),
                    })
            else:
                all_series = computed_data.get("series") or []
                for metric_def in metric_defs:
                    for s in all_series:
                        if s.get("metric_key") == metric_def.key or s.get("type") == metric_def.key:
                            raw_name = s["breakdown_key"]
                            display_name = apply_transform(
                                self.data_source,
                                computed_data.get("breakdown_variable"),
                                raw_name,
                            )
                            chart_series.append({
                                "name": display_name,
                                "data": s.get("data", []),
                                "type": cfg.get("type", "bar"),
                                "stack": cfg.get("stack") or "total",
                            })

            adapted_charts.append({
                "id": chart_id,
                "title": chart_title,
                "type": cfg.get("type", "bar"),
                "years": years,
                "series": chart_series,
                "has_breakdown": has_breakdown,
                "is_relative": False,
            })

            is_relative_supported = True
            for metric_def in metric_defs:
                if isinstance(metric_def, ComputedMetric):
                    is_relative_supported = False
                    break
                if isinstance(metric_def, PhysicalMetric) and metric_def.agg == "avg":
                    is_relative_supported = False
                    break

            if is_relative_supported and relative_metrics and relative_metrics.get("enabled"):
                rel_title = f"{chart_title} (%)"

                rel_series = []
                if not has_breakdown:
                    for metric_def in metric_defs:
                        rel_key = f"{metric_def.key}_share_pct_per_year"
                        rel_vals = relative_metrics.get(rel_key) or []
                        rel_series.append({
                            "name": f"{metric_def.get_label(lang)} (%)",
                            "data": rel_vals,
                            "type": cfg.get("type", "bar"),
                            "isPercentSeries": True,
                            **({"stack": cfg.get("stack")} if cfg.get("stack") else {}),
                        })
                else:
                    all_rel_series = relative_metrics.get("series") or []
                    for metric_def in metric_defs:
                        for s in all_rel_series:
                            if s.get("metric_key") == metric_def.key or s.get("type") == metric_def.key:
                                raw_name = s["breakdown_key"]
                                display_name = apply_transform(
                                    self.data_source,
                                    computed_data.get("breakdown_variable"),
                                    raw_name,
                                )
                                rel_series.append({
                                    "name": display_name,
                                    "data": s.get("data", []),
                                    "type": cfg.get("type", "bar"),
                                    "stack": cfg.get("stack") or "total",
                                    "isPercentSeries": True,
                                })

                adapted_charts.append({
                    "id": f"{chart_id}_share",
                    "title": rel_title,
                    "type": cfg.get("type", "bar"),
                    "years": years,
                    "series": rel_series,
                    "has_breakdown": has_breakdown,
                    "is_relative": True,
                })

        return {
            "years": years,
            "charts": adapted_charts,
            "has_breakdown": has_breakdown,
            "breakdown_variable": computed_data.get("breakdown_variable"),
            "breakdown_keys": computed_data.get("breakdown_keys") or [],
            "relative_metrics": relative_metrics,
        }
