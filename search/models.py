import logging

from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.models import Page
from django.conf import settings
from search_gateway.filters import FILTER_CATEGORIES
from search_gateway.service import SearchGatewayService

logger = logging.getLogger(__name__)


def get_save_number(item, default: int):
    try:
        return int(item)
    except (TypeError, ValueError):
        return default


class SearchPage(RoutablePageMixin, Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        search_query = request.GET.get("search", "")
        index_name = kwargs.get("index_name") or request.GET.get(
            "index_name", getattr(settings, "OP_INDEX_ALL_BRONZE", "bronze_sc*")
        )
        service = SearchGatewayService(index_name=index_name)
        filters = service.build_filters()
        filter_metadata = service.get_filter_metadata(filters)
        selected_filters = service.extract_selected_filters(request=request, available_filters=filters)
        context.update({
            "filters": filters,
            "index_name": index_name,
            "filter_metadata": filter_metadata,
            "display_name": service.display_name,
            "search_query": search_query,
            "filter_categories": FILTER_CATEGORIES,
            "grouped_filters": self.group_filters_by_category(filters, filter_metadata),
            "results_data": service.search_documents(
                query_text=search_query,
                filters=selected_filters,
                page=get_save_number(request.GET.get("page"), 1),
                page_size=get_save_number(request.GET.get("limit"), 25),
            ),
        })
        return context

    @route(r'^$')
    def index_route(self, request):
        return self.render(request)

    @route(r'^world/$')
    def world_route(self, request):
        return self.render(request, index_name=getattr(settings, "OP_INDEX_ALL_BRONZE", ""))

    @route(r'^social/$')
    def social_route(self, request):
        return self.render(request, index_name=getattr(settings, "OP_INDEX_SOC_PROD", ""))

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
