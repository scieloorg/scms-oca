import json
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page

from search_gateway.filters import FILTER_CATEGORIES
from search_gateway.models import DataSource
from search_gateway.service import SearchGatewayService

logger = logging.getLogger(__name__)


def get_save_number(item, default: int):
    try:
        return int(item)
    except (TypeError, ValueError):
        return default


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

    def _build_search_context(self, request):
        """Return the search-specific context dict.

        When no data_source is configured every value is an empty default
        so templates can render safely without conditionals.
        """
        search_query = request.GET.get("search", "")
        filters = {}
        filter_metadata = {}
        results_data = {"search_results": [], "total_results": 0}
        index_name = ""
        display_name = ""

        if self.data_source:
            service = SearchGatewayService(index_name=self.data_source.index_name)
            filters = service.build_filters()
            filter_metadata = service.get_filter_metadata(filters)
            selected_filters = service.extract_selected_filters(
                request=request, available_filters=filters,
            )
            results_data = service.search_documents(
                query_text=search_query,
                filters=selected_filters,
                page=get_save_number(request.GET.get("page"), 1),
                page_size=get_save_number(request.GET.get("limit"), 25),
                sort_field="publication_year",
                sort_order="desc",
            )
            index_name = self.data_source.index_name
            display_name = service.display_name
        else:
            logger.warning(f"SearchPage '{self.title}' has no data_source configured.")

        return {
            "filters": filters,
            "index_name": index_name,
            "filter_metadata": filter_metadata,
            "display_name": display_name,
            "search_query": search_query,
            "filter_categories": FILTER_CATEGORIES,
            "grouped_filters": self.group_filters_by_category(filters, filter_metadata),
            "results_data": results_data,
        }

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update(self._build_search_context(request))
        return context

    def group_filters_by_category(self, filters, filter_metadata):
        """Group filters by their category property."""
        categorized = {}

        ordered_filters = sorted(
            filters.items(),
            key=lambda item: (
                filter_metadata.get(item[0], {}).get("order", float("inf")),
                item[0],
            ),
        )

        for key, options in ordered_filters:
            metadata = filter_metadata.get(key, {})
            category = metadata.get("category", "other")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append((key, options))
        return categorized
