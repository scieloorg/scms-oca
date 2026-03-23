import json
import logging
import math

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page

from .choices import SEARCHABLE_FIELDS
from search_gateway.forms import render_filter_sidebar
from search_gateway.models import DataSource
from search_gateway.request_filters import extract_applied_filters
from search_gateway.request_filters import normalize_option_filters
from search_gateway.service import SearchGatewayService

logger = logging.getLogger(__name__)


def get_save_number(item, default: int):
    try:
        return int(item)
    except (TypeError, ValueError):
        return default


def _read_source_path(payload, *path):
    current = payload
    for part in path:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _normalize_text(value):
    normalized = str(value or "").strip()
    return normalized


def _get_existing_display_source_name(source_payload):
    for candidate in (
        source_payload.get("resolved_source_name"),
        source_payload.get("primary_source_title"),
        _read_source_path(source_payload, "primary_location", "source", "display_name"),
        _read_source_path(source_payload, "primary_location", "source", "title"),
    ):
        normalized = _normalize_text(candidate)
        if normalized:
            return normalized

    source_name = _normalize_text(source_payload.get("source_name"))
    if source_name and not source_name.startswith("http"):
        return source_name
    return ""


def _collect_source_lookup_values(source_payload):
    values = []

    for candidate in (
        _read_source_path(source_payload, "primary_location", "source", "id"),
        source_payload.get("source_name"),
    ):
        normalized = _normalize_text(candidate)
        if normalized:
            values.append(normalized)

    for source_item in source_payload.get("sources") or []:
        if isinstance(source_item, dict):
            for candidate in (
                source_item.get("id"),
                source_item.get("source_id"),
                _read_source_path(source_item, "source", "id"),
            ):
                normalized = _normalize_text(candidate)
                if normalized:
                    values.append(normalized)
        else:
            normalized = _normalize_text(source_item)
            if normalized:
                values.append(normalized)

    return list(dict.fromkeys(values))


def _normalize_positive_number(value, default):
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default
    return normalized if normalized > 0 else default


class SearchPage(Page):
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_pages",
        verbose_name=_("Data Source"),
        help_text=_("Fonte de dados OpenSearch associada a esta página de busca."),
    )

    content_panels = Page.content_panels + [
        FieldPanel("data_source"),
    ]

    @staticmethod
    def query_clauses(request):
        raw_clauses = request.GET.get("search_clauses")
        if not raw_clauses:
            return []

        try:
            clauses = json.loads(raw_clauses)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

        return clauses if isinstance(clauses, list) else []

    @staticmethod
    def enrich_results_data_for_display(data_source, results_data):
        if not data_source:
            return results_data

        search_results = list((results_data or {}).get("search_results") or [])
        if not search_results:
            return results_data

        source_field = data_source.get_field("source_name")
        if not source_field or not source_field.get_lookup_config():
            return results_data

        pending_results = []
        lookup_values = []

        for result in search_results:
            source_payload = result.get("source") or {}
            if _get_existing_display_source_name(source_payload):
                continue

            source_lookup_values = _collect_source_lookup_values(source_payload)
            if not source_lookup_values:
                continue

            pending_results.append((source_payload, source_lookup_values))
            lookup_values.extend(source_lookup_values)

        if not lookup_values:
            return results_data

        service = SearchGatewayService(index_name=data_source.index_name)
        lookup_options, error = service.get_lookup_options_by_values(
            "source_name",
            list(dict.fromkeys(lookup_values)),
        )
        if error or not lookup_options:
            return results_data

        label_by_value = {
            _normalize_text(option.get("key")): _normalize_text(option.get("label") or option.get("key"))
            for option in lookup_options
            if _normalize_text(option.get("key"))
        }

        for source_payload, source_lookup_values in pending_results:
            for lookup_value in source_lookup_values:
                resolved_label = label_by_value.get(lookup_value)
                if resolved_label:
                    source_payload["resolved_source_name"] = resolved_label
                    break

        return results_data

    @staticmethod
    def decorate_results_data_for_ui(results_data, *, page=1, page_size=25, sort="recent"):
        decorated = results_data or {"search_results": [], "total_results": 0}
        search_results = list(decorated.get("search_results") or [])
        total_results = _normalize_positive_number(decorated.get("total_results"), 0)
        current_page = _normalize_positive_number(page, 1)
        current_limit = _normalize_positive_number(page_size, 25)
        shown_count = len(search_results)

        start_result = ((current_page - 1) * current_limit) + 1 if shown_count else 0
        end_result = start_result + shown_count - 1 if shown_count else 0
        total_pages = int(math.ceil(total_results / current_limit)) if total_results and current_limit else 0

        current_sort = str(sort or "recent").strip().lower()
        if current_sort not in {"recent", "oldest", "cited"}:
            current_sort = "recent"

        page_numbers = []
        if total_pages:
            window_start = max(1, current_page - 2)
            window_end = min(total_pages, current_page + 2)

            while (window_end - window_start) < 4 and window_start > 1:
                window_start -= 1
            while (window_end - window_start) < 4 and window_end < total_pages:
                window_end += 1

            page_numbers = list(range(window_start, window_end + 1))

        decorated.update({
            "current_page": current_page,
            "current_limit": current_limit,
            "current_sort": current_sort,
            "shown_count": shown_count,
            "start_result": start_result,
            "end_result": end_result,
            "total_pages": total_pages,
            "page_numbers": page_numbers,
            "has_previous": current_page > 1,
            "has_next": total_pages > current_page,
            "previous_page": current_page - 1 if current_page > 1 else 1,
            "next_page": current_page + 1 if total_pages > current_page else total_pages,
        })
        return decorated

    @classmethod
    def _build_search_context_for_data_source(cls, request, data_source):
        """Return the search-specific context dict for a given data source."""
        search_query = request.GET.get("search", "")
        results_data = {"search_results": [], "total_results": 0}
        index_name = ""
        query_clauses = cls.query_clauses(request)
        is_scientific_data_source = False
        search_sidebar_html = ""

        if data_source:
            service = SearchGatewayService(index_name=data_source.index_name)
            applied_filters = extract_applied_filters(request.GET, data_source, form_key="search")
            selected_filters = normalize_option_filters(applied_filters)
            current_page = get_save_number(request.GET.get("page"), 1)
            current_limit = get_save_number(request.GET.get("limit"), 25)
            current_sort = request.GET.get("sort", "recent")
            sidebar_payload = render_filter_sidebar(
                request,
                data_source=data_source,
                form_key="search",
                applied_filters=applied_filters,
                sidebar_form_id="search-filter-form",
                sidebar_form_method="get",
                submit_label=_("APLICAR"),
                reset_label=_("LIMPAR"),
                submit_id="search-filter-submit",
                reset_id="search-filter-reset",
                reset_type="button",
            )
            search_sidebar_html = sidebar_payload["form_html"]
            results_data = service.search_documents(
                query_text=search_query if not query_clauses else None,
                query_clauses=query_clauses,
                filters=selected_filters,
                page=current_page,
                page_size=current_limit,
                sort_field="publication_year",
                sort_order="desc",
            )
            results_data = cls.enrich_results_data_for_display(data_source, results_data)
            results_data = cls.decorate_results_data_for_ui(
                results_data,
                page=current_page,
                page_size=current_limit,
                sort=current_sort,
            )
            index_name = data_source.index_name
            is_scientific_data_source = (
                index_name == getattr(settings, "OP_INDEX_SCIENTIFIC_PRODUCTION", "scientific_production")
            )
        else:
            logger.warning("SearchPage context requested without a configured data_source.")

        return {
            "index_name": index_name,
            "searchable_fields": SEARCHABLE_FIELDS,
            "search_clauses": query_clauses,
            "is_scientific_data_source": is_scientific_data_source,
            "search_query": search_query,
            "search_sidebar_html": search_sidebar_html,
            "results_data": results_data,
        }

    def get_context(self, request, *args, **kwargs):
        if not self.data_source:
            logger.warning(f"SearchPage '{self.title}' has no data_source configured.")

        context = super().get_context(request, *args, **kwargs)
        context.update(
            self._build_search_context_for_data_source(request, self.data_source)
        )
        return context
