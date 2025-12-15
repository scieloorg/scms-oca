import logging
from typing import List, Optional

from wagtail.models import Page

from search_gateway import controller
from search_gateway.data_sources_with_settings import (
    DATA_SOURCES,
    get_index_name_from_data_source,
    get_result_template_by_data_source,
)
from search_gateway.parser import extract_selected_filters
from search_gateway.service import SearchGatewayService

logger = logging.getLogger(__name__)


def get_save_number(item, default: int):
    try:
        return int(item)
    except (TypeError, ValueError):
        return default

def get_available_data_sources(data_sources=None):
    """
    Get list of available data sources with their display names.
    If data_sources is provided (list or iterable), only return those matching ones.
    """
    if data_sources is not None:
        keys = set(data_sources)
        return [
            {"key": key, "display_name": str(config.get("display_name", key))}
            for key, config in DATA_SOURCES.items() if key in keys
        ]

class SearchPage(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        search_query = request.GET.get("search", "")
        data_source_name = request.GET.get("data_source", "world")
        context["current_data_source"] = get_index_name_from_data_source(data_source_name)
        service = SearchGatewayService(data_source_name=data_source_name)
        self.set_filters(context, service)
        self.set_filters_metadata(context, filters=context.get("filters", {}), service=service)
        selected_filters = extract_selected_filters(request, context.get("filters", {}), data_source_name)
        results_data = self.get_results_data(
            request=request, 
            data_source_name=data_source_name, 
            search_query=search_query, 
            selected_filters=selected_filters,
            source_fields=service.source_fields
        )
        context["data_source_name"] = data_source_name
        context["results_data"] = results_data
        context["search_query"] = search_query
        context["selected_filters"] = selected_filters
        context["result_template"] = get_result_template_by_data_source(data_source_name)
        context["available_data_sources"] = get_available_data_sources(data_sources=["social_production", "world"])
        return context

    def get_filters(self, service, exclude_fields: Optional[List] = None):
        return service.get_filters(exclude_fields=exclude_fields)

    def set_filters(self, context, service, exclude_fields: Optional[List] = None):
        exclude_fields = service.filters_to_exlcude
        body = self.get_filters(service=service, exclude_fields=exclude_fields)
        context['filters'] = service.build_filters(body=body)

    
    def set_filters_metadata(self,context, filters, service):
        metadata = service.get_filter_metadata(filters)
        context['filter_metadata'] = metadata

    @staticmethod
    def get_results_data(request, data_source_name, search_query, selected_filters, source_fields):
        return controller.search_documents(
            data_source_name=data_source_name,
            query_text=search_query,
            filters=selected_filters,
            page=get_save_number(request.GET.get("page"), 1),
            page_size=get_save_number(request.GET.get("limit"), 50),
            source_fields=source_fields
        )
