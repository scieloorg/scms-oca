from dataclasses import dataclass, field as dataclass_field
from typing import Any, Dict, List, Optional, Union


@dataclass
class PhysicalMetric:
    key: str
    field: Optional[str]
    agg: str
    label: Dict[str, str] = dataclass_field(default_factory=dict)
    filter_query: Dict[str, Any] = dataclass_field(default_factory=dict)
    sub_aggs: Dict[str, Any] = dataclass_field(default_factory=dict)
    path: Optional[str] = None

    def get_label(self, lang: str = "pt") -> str:
        return self.label.get(lang) or self.label.get("pt") or self.key


@dataclass
class ComputedMetric:
    key: str
    formula: str
    precision: int
    label: Dict[str, str] = dataclass_field(default_factory=dict)

    def get_label(self, lang: str = "pt") -> str:
        return self.label.get(lang) or self.label.get("pt") or self.key


Metric = Union[PhysicalMetric, ComputedMetric]


class MetricGroup:
    def __init__(
        self,
        key: str,
        time_dimension: Dict[str, Any],
        metrics: List[Metric],
        breakdown_variable: Optional[str] = None,
        sort: Optional[List[Dict[str, Any]]] = None,
        collapse: Optional[Dict[str, Any]] = None,
    ):
        self.key = key
        self.time_dimension = time_dimension or {"field": "publication_year", "agg_type": "terms"}
        self.metrics = metrics or []
        self.breakdown_variable = breakdown_variable
        self.sort = sort or []
        self.collapse = collapse or {}

    @property
    def physical_metrics(self) -> List[PhysicalMetric]:
        return [m for m in self.metrics if isinstance(m, PhysicalMetric)]

    @property
    def computed_metrics(self) -> List[ComputedMetric]:
        return [m for m in self.metrics if isinstance(m, ComputedMetric)]

    def get_metric(self, key: str) -> Optional[Metric]:
        for m in self.metrics:
            if m.key == key:
                return m
        return None

    @classmethod
    def from_config(cls, group_key: str, group_dict: Dict[str, Any], breakdown_variable: Optional[str] = None) -> "MetricGroup":
        metrics_list = []
        raw_metrics = group_dict.get("metrics") or []

        for m_dict in raw_metrics:
            m_type = m_dict.get("type", "physical")
            key = m_dict.get("key")
            label = m_dict.get("label") or {}

            if m_type == "computed":
                metrics_list.append(
                    ComputedMetric(
                        key=key,
                        formula=m_dict.get("formula"),
                        precision=m_dict.get("precision", 4),
                        label=label,
                    )
                )
            else:
                metrics_list.append(
                    PhysicalMetric(
                        key=key,
                        field=m_dict.get("field"),
                        agg=m_dict.get("agg", "count"),
                        label=label,
                        filter_query=m_dict.get("filter_query") or {},
                        sub_aggs=m_dict.get("sub_aggs") or {},
                        path=m_dict.get("path"),
                    )
                )

        return cls(
            key=group_key,
            time_dimension=group_dict.get("time_dimension") or {},
            metrics=metrics_list,
            breakdown_variable=breakdown_variable,
            sort=group_dict.get("sort") or [],
            collapse=group_dict.get("collapse") or {},
        )
