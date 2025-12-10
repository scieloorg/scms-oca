import logging
from typing import List, Optional

from search_gateway import controller
from search_gateway.data_sources_with_settings import (
    field_supports_search_as_you_type,
    get_field_settings,
    get_index_name_from_data_source,
)
from search_gateway.parser import extract_selected_filters
from search_gateway.service import SearchGatewayService
from wagtail.models import Page

logger = logging.getLogger(__name__)


def get_save_number(item, default: int):
    try:
        return int(item)
    except (TypeError, ValueError):
        return default

class SearchPage(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        search_query = request.GET.get("search", "")
        data_source_name = "world"
        context["current_data_source"] = get_index_name_from_data_source(data_source_name)
        service = SearchGatewayService(data_source_name=data_source_name)
        self.set_filters(context, service)
        self.set_filters_metadata(context, filters=context.get("filters", {}), service=service)
        selected_filters = extract_selected_filters(request, context.get("filters", {}), data_source_name)
        results_data = self.get_results_data(
            request, 
            data_source_name, 
            search_query, 
            selected_filters
        )
        context["data_source_name"] = data_source_name
        context["results_data"] = results_data
        context["search_query"] = search_query
        context["selected_filters"] = selected_filters
        return context

    def get_filters(self, service, exclude_fields: Optional[List] = None):
        return service.get_filters(exclude_fields=exclude_fields)

    def set_filters(self, context, service, exclude_fields: Optional[List] = None):
        exclude_fields = exclude_fields or [
                "source_index_scielo",
                "cited_by_count",
                "document_publication_year_start",
                "document_publication_year_end",
                "document_publication_year_range"
            ]
        body = self.get_filters(service=service, exclude_fields=exclude_fields)
        context['filters'] = service.build_filters(body=body)

    
    def set_filters_metadata(self,context, filters, service):
        metadata = service.get_filter_metadata(filters)
        context['filter_metadata'] = metadata

    @staticmethod
    def get_results_data(request, data_source_name, search_query, selected_filters):
        return controller.search_documents(
            data_source_name=data_source_name,
            query_text=search_query,
            filters=selected_filters,
            page=get_save_number(request.GET.get("page"), 1),
            page_size=get_save_number(request.GET.get("limit"), 50),
            source_fields=[
                "_id",
                "primary_location",
                "publication_year",
                "biblio.volume",
                "biblio.issue",
                "biblio.first_page",
                "journal_metadata.issns",
                "journal_metadata.country",
                "title",
                "authorships",
                "language",
                "type",
                "open_access.is_oa",
                "open_access.oa_status",
                "indexed_in",
                "locations.landing_page_url",
            ],
        )
