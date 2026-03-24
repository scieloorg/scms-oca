import json
import logging
import math

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page

from search_gateway.filter_ui import render_filter_sidebar
from search_gateway.models import DataSource
from search_gateway.option_normalization import (
    normalize_positive_number,
    normalize_search_result_sort,
)
from search_gateway.request_filters import extract_applied_filters
from search_gateway.request_filters import normalize_option_filters
from search_gateway.service import SearchGatewayService

from .choices import SEARCHABLE_FIELDS


logger = logging.getLogger(__name__)


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

    @classmethod
    def get_search_request_state(cls, request):
        return {
            "search_query": request.GET.get("search", ""),
            "query_clauses": cls.query_clauses(request),
            "current_sort": normalize_search_result_sort(request.GET.get("sort", "recent")),
            "current_page": normalize_positive_number(request.GET.get("page"), 1),
            "current_limit": normalize_positive_number(request.GET.get("limit"), 25),
        }

    @staticmethod
    def current_pagination(results_data, *, page=1, page_size=25, sort="recent"):
        decorated = results_data or {"search_results": [], "total_results": 0}
        search_results = list(decorated.get("search_results") or [])
        total_results = normalize_positive_number(decorated.get("total_results"), 0)
        current_page = page
        current_limit = page_size
        shown_count = len(search_results)

        start_result = ((current_page - 1) * current_limit) + 1 if shown_count else 0
        end_result = start_result + shown_count - 1 if shown_count else 0
        total_pages = int(math.ceil(total_results / current_limit)) if total_results and current_limit else 0

        current_sort = normalize_search_result_sort(sort)

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

    @staticmethod
    def build_search_template_context(
        request_state,
        *,
        index_name="",
        search_sidebar_html="",
        results_data=None,
    ):
        scientific_index = getattr(settings, "OP_INDEX_SCIENTIFIC_PRODUCTION", "scientific_production")
        payload = {"search_results": [], "total_results": 0} if results_data is None else results_data
        return {
            "index_name": index_name,
            "searchable_fields": SEARCHABLE_FIELDS,
            "search_clauses": request_state["query_clauses"],
            "is_scientific_data_source": index_name == scientific_index,
            "search_query": request_state["search_query"],
            "search_sidebar_html": search_sidebar_html,
            "results_data": payload,
        }

    def render_search_filter_sidebar_html(self, request, data_source, applied_filters):
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
        return sidebar_payload["form_html"]

    def fetch_gateway_search_results(self, data_source, request_state, selected_filters):
        service = SearchGatewayService(index_name=data_source.index_name)
        return service.search_documents(
            query_text=request_state["search_query"] if not request_state["query_clauses"] else None,
            query_clauses=request_state["query_clauses"],
            filters=selected_filters,
            page=request_state["current_page"],
            page_size=request_state["current_limit"],
            sort_field="publication_year",
            sort_order="desc",
        )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        request_state = self.get_search_request_state(request)
        data_source = self.data_source

        if not data_source:
            logger.warning(f"SearchPage '{self.title}' has no data_source configured.")
            context.update(self.build_search_template_context(request_state))
            return context

        applied_filters = extract_applied_filters(request.GET, data_source, form_key="search")
        selected_filters = normalize_option_filters(applied_filters)
        sidebar_html = self.render_search_filter_sidebar_html(request, data_source, applied_filters)
        raw_results = self.fetch_gateway_search_results(data_source, request_state, selected_filters)
        results_data = self.current_pagination(
            raw_results,
            page=request_state["current_page"],
            page_size=request_state["current_limit"],
            sort=request_state["current_sort"],
        )
        context.update(
            self.build_search_template_context(
                request_state,
                index_name=data_source.index_name,
                search_sidebar_html=sidebar_html,
                results_data=results_data,
            )
        )
        return context
