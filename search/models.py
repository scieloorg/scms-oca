import logging
from typing import List, Optional

from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.models import Page

from search_gateway import controller
from search_gateway.data_sources_with_settings import (
    DATA_SOURCES,
    get_index_name_from_data_source,
    get_result_template_by_data_source,
)
from search_gateway.filters import FILTER_CATEGORIES
from search_gateway.parser import extract_selected_filters
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
        data_source_name = kwargs.get("data_source_name") or request.GET.get("data_source", "bronze_*")
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
            source_fields=service.source_fields,
            client=service.client,
        )
        context["data_source_name"] = data_source_name
        context["display_name"] = service.display_name
        context["results_data"] = results_data
        context["search_query"] = search_query
        context["filter_categories"] = FILTER_CATEGORIES
        context["grouped_filters"] = self.group_filters_by_category(
            context.get("filters", {}), 
            context.get("filter_metadata", {})
        )
        return context

    @route(r'^$')
    def index_route(self, request):
        """Default route - uses data_source from GET param or defaults to 'world'"""
        return self.render(request)

    @route(r'^world/$')
    def world_route(self, request):
        """World data source route"""
        return self.render(request, data_source_name="bronze_all")

    @route(r'^social/$')
    def social_route(self, request):
        """Social production data source route"""
        return self.render(request, data_source_name="bronze_social_production")

    def get_filters(self, service, exclude_fields: Optional[List] = None):
        return service.get_filters(exclude_fields=exclude_fields)

    def set_filters(self, context, service, exclude_fields: Optional[List] = None):
        exclude_fields = service.filters_to_exclude
        body = self.get_filters(service=service, exclude_fields=exclude_fields)
        context['filters'] = service.build_filters(body=body)

    
    def set_filters_metadata(self,context, filters, service):
        metadata = service.get_filter_metadata(filters)
        context['filter_metadata'] = metadata
    
    def group_filters_by_category(self, filters, filter_metadata):
        """Group filters by their category property"""
        categorized = {}
        
        for key, options in filters.items():
            metadata = filter_metadata.get(key, {})
            category = metadata.get('category', 'other')
            
            if category not in categorized:
                categorized[category] = []
            categorized[category].append((key, options))
        
        return categorized

    @staticmethod
    def get_results_data(request, data_source_name, search_query, selected_filters, source_fields, client):
        return controller.search_documents(
            data_source_name=data_source_name,
            query_text=search_query,
            filters=selected_filters,
            page=get_save_number(request.GET.get("page"), 1),
            page_size=get_save_number(request.GET.get("limit"), 50),
            source_fields=source_fields,
            client=client
        )
