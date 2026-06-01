from typing import Any, Dict, List

from django.http import QueryDict
from django.utils import formats
from django.utils.translation import gettext as _
from search_gateway.transforms import apply_transform

from .config import JournalMetricConfig


class JournalMetricPresentation:
    def __init__(self, data_source: Any = None):
        self.data_source = data_source
        self.config = JournalMetricConfig(data_source) if data_source else None

    def format_metric_value(self, value: Any, decimal_pos: int = 0, is_percent: bool = False) -> str:
        if value in (None, ""):
            return "-"

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return "-"

        if decimal_pos == 0:
            numeric_value = int(round(numeric_value))

        formatted = formats.number_format(numeric_value, decimal_pos=decimal_pos, use_l10n=True, force_grouping=True)
        return f"{formatted}%" if is_percent else formatted

    def build_collection_display(self, profile_data: Dict[str, Any], selected_year_metrics: Dict[str, Any]) -> str:
        source = selected_year_metrics or (profile_data or {})
        collection_name = str(source.get("collection_name") or "").strip()
        collection_acronym = str(source.get("collection_acronym") or "").strip()
        collection_code = str(source.get("collection") or "").strip()

        transformed = str(
            apply_transform(self.data_source.index_name, "collection", collection_code) or ""
        ).strip()
        if transformed and transformed.lower() != collection_code.lower():
            return transformed

        normalized_values = {
            value.lower()
            for value in (collection_name, collection_acronym, collection_code)
            if value
        }

        if len(normalized_values) == 1:
            return collection_name or collection_acronym or collection_code

        if collection_name and collection_acronym:
            return f"{collection_name} ({collection_acronym})"
        return collection_name or collection_acronym or collection_code

    def build_profile_url(self, params: QueryDict, issn: str, profile_base_url: str = "") -> str:
        if not profile_base_url:
            return ""

        query_params = QueryDict("", mutable=True)
        query_params["journal"] = str(issn).strip()
        for key in self.config.profile_query_params():
            val = params.get(key)
            if val not in (None, ""):
                query_params[key] = str(val)

        query_string = query_params.urlencode()
        return f"{profile_base_url}?{query_string}" if query_string else profile_base_url

    def build_profile_context(
        self,
        journal_issn: str,
        profile_data: Dict[str, Any],
        selected_category_level: str,
        selected_category_id: str,
        selected_publication_year: str,
        passthrough_filters: Dict[str, str],
        filters_data: Dict[str, Any],
        filters_error: str = None,
        profile_error: str = None,
        global_snapshot: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        resolved_category_level = selected_category_level or self.config.field_default("category_level")
        resolved_category_id = selected_category_id
        resolved_publication_year = selected_publication_year

        year_options = []
        category_level_options = []
        category_options = []

        if filters_data:
            year_options = sorted(
                [str(opt.get("value")) for opt in filters_data.get("publication_year", []) if opt.get("value") is not None],
                reverse=True,
            )
            category_level_options = sorted(
                [str(opt.get("value")) for opt in filters_data.get("category_level", []) if opt.get("value") is not None]
            )
            category_options = sorted(
                [str(opt.get("value")) for opt in filters_data.get("category_id", []) if opt.get("value") is not None]
            )

        if profile_data:
            if profile_data.get("available_category_levels"):
                category_level_options = sorted(list(profile_data["available_category_levels"]))
            if profile_data.get("available_categories"):
                category_options = sorted(list(profile_data["available_categories"]))

        if not resolved_category_id and category_options:
            resolved_category_id = category_options[0]
        if not resolved_publication_year and year_options:
            resolved_publication_year = year_options[0]

        snapshots = profile_data.get("annual_snapshots", []) if profile_data else []
        selected_year_metrics = next(
            (s for s in snapshots if str(s.get("publication_year")) == resolved_publication_year),
            None,
        )

        kpis = []
        if profile_data:
            source = selected_year_metrics or profile_data
            kpis = self.build_metric_cards(source, self.config.profile_section("kpis"))

        header_attrs = []
        if profile_data:
            header_attrs = self.build_header_attributes(
                profile_data,
                selected_year_metrics,
                self.config.profile_section("header_attributes"),
            )

        resolved_global_publication_year = resolved_publication_year
        global_year_options = []
        global_kpis = []
        global_badges = {"attributes": [], "indexing": []}
        global_timeseries = None

        if global_snapshot:
            all_sources = global_snapshot.get("_all_sources", [])
            global_years = {str(s.get("publication_year")) for s in all_sources if s.get("publication_year")}
            global_year_options = sorted(list(global_years), reverse=True)

            if resolved_global_publication_year not in global_years and global_year_options:
                resolved_global_publication_year = global_year_options[0]

            year_source = next(
                (s for s in all_sources if str(s.get("publication_year")) == resolved_global_publication_year),
                None,
            )
            if year_source:
                global_kpis = self.build_metric_cards(year_source, self.config.profile_section("global_kpis"))
                global_badges = self.build_badges(year_source, self.config.profile_badges())

            global_timeseries = self.build_timeseries_payload(
                all_sources,
                self.config.profile_section("global_timeseries"),
            )

        context = {
            "journal_issn": journal_issn,
            "journal_title": profile_data.get("journal_title") if profile_data else None,
            "selected_category_id": resolved_category_id,
            "selected_category_level": resolved_category_level,
            "selected_publication_year": resolved_publication_year,
            "profile_passthrough_filters": passthrough_filters,
            "profile_data": profile_data,
            "profile_header_attributes": header_attrs,
            "profile_kpis": kpis,
            "profile_badges": {"attributes": [], "indexing": []},
            "profile_year_options": year_options,
            "profile_category_level_options": category_level_options,
            "profile_category_options": category_options,
            "filters_data": filters_data or {},
            "global_snapshot": global_snapshot,
            "selected_global_publication_year": resolved_global_publication_year,
            "global_year_options": global_year_options,
            "global_kpis": global_kpis,
            "global_badges": global_badges,
            "global_timeseries": global_timeseries,
            "profile_timeseries_charts": self.config.profile_chart_section("timeseries"),
            "profile_category_charts": self.config.profile_chart_section("category_charts"),
            "global_timeseries_charts": self.config.profile_chart_section("global_timeseries_charts"),
        }

        if filters_error:
            context["filters_error"] = _("Error loading filters: %s") % filters_error
        if profile_error:
            context["error"] = _("Error executing search: %s") % profile_error

        return context

    def build_metric_cards(self, source: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cards = []
        for item in items:
            field = item.get("field")
            cards.append({
                "label": self.config.localized_label(item, default=self.config.field_label(field)),
                "value": self.format_metric_value(
                    source.get(field),
                    decimal_pos=int(item.get("decimals", 0)),
                    is_percent=bool(item.get("is_percent")),
                ),
            })
        return cards

    def build_header_attributes(
        self,
        profile_data: Dict[str, Any],
        selected_year_metrics: Dict[str, Any],
        items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        attrs = []
        source = selected_year_metrics or profile_data or {}
        for item in items:
            field = item.get("field")
            if item.get("display") == "collection":
                value = self.build_collection_display(profile_data, selected_year_metrics)
            else:
                value = source.get(field) or profile_data.get(field)

            if value in (None, "", [], {}):
                continue

            attrs.append({
                "label": self.config.localized_label(item, default=self.config.field_label(field)),
                "value": value,
            })
        return attrs

    def build_badges(self, source: Dict[str, Any], groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        return {
            group_key: [
                {
                    "label": self.config.localized_label(item, default=self.config.field_label(item.get("field"))),
                    "active": bool(source.get(item.get("field"))),
                }
                for item in items
            ]
            for group_key, items in groups.items()
        }

    def build_timeseries_payload(self, sources: List[Dict[str, Any]], items: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {"years": [str(source.get("publication_year") or "") for source in sources]}
        for item in items:
            key = str(item.get("key") or item.get("field") or "").strip()
            field = str(item.get("field") or "").strip()
            if key and field:
                payload[key] = [source.get(field) for source in sources]
        return payload

    def build_ranking_context(
        self,
        applied_filters: Dict[str, Any],
        ranking_data: Dict[str, Any],
        profile_base_url: str = "",
    ) -> Dict[str, Any]:
        ranking_configuration = {}
        display_applied_filters = {}
        ranking_configuration_keys = set(self.config.ranking_configuration_keys())

        for key, value in (applied_filters or {}).items():
            target = ranking_configuration if key in ranking_configuration_keys else display_applied_filters
            target[key] = value

        if ranking_data:
            passthrough_filters = {
                key: value
                for key in self.config.passthrough_params()
                for value in [(applied_filters or {}).get(key)]
                if value not in (None, "")
            }
            ranking_publication_year = ranking_data.get("year") or applied_filters.get("publication_year")

            for entry in ranking_data.get("journals", []):
                journal_identifier = str(entry.get("issn") or entry.get("journal_id") or "").strip()
                if not journal_identifier:
                    entry["profile_url"] = ""
                    continue

                query_params = QueryDict("", mutable=True)
                for key, value in passthrough_filters.items():
                    query_params[key] = str(value)

                for key, value in (
                    ("collection", entry.get("collection")),
                    ("category_id", entry.get("category_id") or ranking_configuration.get("category_id")),
                    ("category_level", entry.get("category_level") or ranking_configuration.get("category_level")),
                    ("publication_year", ranking_publication_year),
                ):
                    if value not in (None, "") and key not in query_params:
                        query_params[key] = str(value)

                entry["profile_url"] = self.build_profile_url(
                    query_params,
                    journal_identifier,
                    profile_base_url=profile_base_url,
                )

        return {
            "ranking_configuration": ranking_configuration,
            "display_applied_filters": display_applied_filters,
            "ranking_columns": self.build_ranking_columns(ranking_data or {}),
        }

    def build_ranking_columns(self, ranking_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        columns = []
        ranking_metric = (ranking_data or {}).get("ranking_metric")
        for column in self.config.ranking_columns():
            normalized = dict(column)
            if column.get("ranking_metric"):
                normalized["field"] = ranking_metric
                normalized["label"] = self.config.option_label("ranking_metric", ranking_metric)
            columns.append(normalized)
        return columns
