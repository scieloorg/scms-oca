from dataclasses import dataclass
from typing import Any, Dict, List

from django.utils.translation import get_language


class JournalMetricConfigError(ValueError):
    pass


@dataclass(frozen=True)
class JournalMetricConfig:
    data_source: Any

    @property
    def schema(self) -> Dict[str, Any]:
        return self.data_source.metric_config_schema or {}

    def require(self, *path: str) -> Any:
        current = self.schema
        for part in path:
            if not isinstance(current, dict) or part not in current:
                raise JournalMetricConfigError(
                    f"Missing journal metric config: {'.'.join(path)}"
                )
            current = current[part]
        if current in (None, "", [], {}):
            raise JournalMetricConfigError(
                f"Empty journal metric config: {'.'.join(path)}"
            )
        return current

    def optional(self, *path: str, default: Any = None) -> Any:
        current = self.schema
        for part in path:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return default if current in (None, "") else current

    def form_key(self, name: str) -> str:
        return str(self.require("journal", "forms", name)).strip()

    def related_global_data_source(self) -> str:
        return str(self.require("journal", "related_global_data_source")).strip()

    def passthrough_params(self) -> List[str]:
        return self._string_list(self.optional("journal", "profile_passthrough_params", default=[]))

    def profile_query_params(self) -> List[str]:
        return self._string_list(self.require("journal", "profile_query_params"))

    def ranking_configuration_keys(self) -> List[str]:
        return self._string_list(self.require("displays", "ranking", "configuration_keys"))

    def ranking_columns(self) -> List[Dict[str, Any]]:
        columns = self.require("displays", "ranking", "columns")
        if not isinstance(columns, list):
            raise JournalMetricConfigError("displays.ranking.columns must be a list")
        return [self._normalize_column(column) for column in columns]

    def profile_section(self, section: str) -> List[Dict[str, Any]]:
        items = self.optional("displays", "profile", section, default=[])
        if not isinstance(items, list):
            raise JournalMetricConfigError(f"displays.profile.{section} must be a list")
        return [dict(item) for item in items if isinstance(item, dict)]

    def profile_badges(self) -> Dict[str, List[Dict[str, Any]]]:
        badges = self.optional("displays", "profile", "badges", default={})
        if not isinstance(badges, dict):
            raise JournalMetricConfigError("displays.profile.badges must be an object")
        return {
            str(group_key): [dict(item) for item in group_items if isinstance(item, dict)]
            for group_key, group_items in badges.items()
            if isinstance(group_items, list)
        }

    def profile_chart_section(self, section: str) -> List[Dict[str, Any]]:
        charts = self.optional("displays", "profile", section, default=[])
        if not isinstance(charts, list):
            raise JournalMetricConfigError(f"displays.profile.{section} must be a list")
        return [self._normalize_chart(chart) for chart in charts if isinstance(chart, dict)]

    def analysis_units(self, url_context: Dict[str, str], current_value: str = "") -> List[Dict[str, Any]]:
        units = self.optional("navigation", "analysis_units", default=[])
        if not isinstance(units, list):
            raise JournalMetricConfigError("navigation.analysis_units must be a list")

        return [
            self._normalize_analysis_unit(unit, url_context, current_value)
            for unit in units
            if isinstance(unit, dict) and unit.get("enabled", True) is not False
        ]

    def field_label(self, field_name: str) -> str:
        field = self.data_source.get_field(field_name)
        return field.label if field else field_name

    def option_label(self, field_name: str, value: str) -> str:
        field = self.data_source.get_field(field_name)
        if field:
            for option in field.static_options:
                if str(option.get("value") or "") == str(value):
                    return str(option.get("label") or value)
        return str(value)

    def field_default(self, field_name: str, default: Any = "") -> Any:
        field = self.data_source.get_field(field_name)
        if not field or field.default_value in (None, "", [], {}):
            return default
        return field.default_value

    def localized_label(self, item: Dict[str, Any], default: str = "") -> str:
        label = item.get("label")
        return self.localized_text(label, default=default if default else self.field_label(item.get("field")))

    def localized_text(self, value: Any, default: str = "") -> str:
        if isinstance(value, dict):
            lang = (get_language() or "pt").split("-")[0]
            return str(value.get(lang) or value.get("pt") or value.get("en") or default)
        if value not in (None, ""):
            return str(value)
        return default

    def _normalize_chart(self, chart: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(chart)
        normalized["title"] = self.localized_text(chart.get("title"), default=str(chart.get("chart_id") or ""))
        normalized["label"] = self.localized_label(
            chart,
            default=self.field_label(str(chart.get("field") or "").strip()),
        )
        if "decimals" in normalized:
            normalized["decimals"] = int(normalized.get("decimals") or 0)

        series = []
        for item in chart.get("series") or []:
            if not isinstance(item, dict):
                continue
            series_item = dict(item)
            field = str(series_item.get("field") or series_item.get("key") or "").strip()
            series_item["label"] = self.localized_label(series_item, default=self.field_label(field))
            series_item["decimals"] = int(series_item.get("decimals", 0))
            series.append(series_item)
        normalized["series"] = series

        y_axes = []
        for item in chart.get("y_axes") or []:
            if not isinstance(item, dict):
                continue
            y_axis = dict(item)
            y_axis["label"] = self.localized_text(y_axis.get("label"), default="")
            y_axis["decimals"] = int(y_axis.get("decimals", 0))
            y_axes.append(y_axis)
        normalized["y_axes"] = y_axes
        return normalized

    def _normalize_column(self, column: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(column, dict):
            raise JournalMetricConfigError("ranking column entries must be objects")
        field_name = str(column.get("field") or "").strip()
        if not field_name:
            raise JournalMetricConfigError("ranking column missing field")
        normalized = dict(column)
        normalized["field"] = field_name
        normalized["label"] = self.localized_label(column, default=field_name)
        normalized["decimals"] = None if column.get("decimals") is None else int(column.get("decimals", 0))
        return normalized

    def _normalize_analysis_unit(
        self,
        unit: Dict[str, Any],
        url_context: Dict[str, str],
        current_value: str,
    ) -> Dict[str, Any]:
        value = str(unit.get("value") or "").strip()
        url_key = str(unit.get("url_context_key") or "").strip()
        return {
            "value": value,
            "label": self.localized_label(unit, default=value),
            "url": url_context.get(url_key, ""),
            "selected": value == current_value,
            "return_to_source": bool(unit.get("return_to_source")),
        }

    def _string_list(self, values: Any) -> List[str]:
        if not isinstance(values, list):
            raise JournalMetricConfigError("Expected a list in journal metric config")
        return [str(value).strip() for value in values if str(value or "").strip()]
