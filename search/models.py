from search_gateway import controller
from search_gateway.data_sources_with_settings import (
    field_supports_search_as_you_type,
    get_field_settings,
    get_index_name_from_data_source,
)
from wagtail.models import Page


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
        self.set_filters(context, data_source_name)
        self.set_filters_search_as_you_type(context, data_source_name)

        selected_filters = self.extract_selected_filters(request, context.get("filters", {}))
        self.set_filters_metadata(context, data_source_name)
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

    def set_filters(self, context, data_source_name):
        """
        Fetches available filter options (aggregations) from Elasticsearch.
        """
        filters, erros = controller.get_filters_data(
            data_source_name,
            exclude_fields=[
                "source_index_scielo",
                "cited_by_count",
                "document_publication_year_start",
                "document_publication_year_end"
            ],
        )
        context["filters"] = filters

    def set_filters_metadata(self, context, data_source_name):
        field_settings = get_field_settings(data_source_name)
        filter_metadata = {}

        for field_name in context.get("filters", {}).keys():
            if field_name in field_settings:
                filter_config = field_settings[field_name].get("filter", {})
                class_filter = filter_config.get("class_filter", "select2")
                filter_metadata[field_name] = {
                    "class_filter": class_filter
                }
        context["filter_metadata"] = filter_metadata


    def set_filters_search_as_you_type(self, context, data_source_name):
        autocomplete_fields = {}
        if "filters" in context:
            for field_name in context["filters"].keys():
                if field_supports_search_as_you_type(data_source_name, field_name):
                    autocomplete_fields[field_name] = True
        context["autocomplete_fields"] = autocomplete_fields


    def extract_selected_filters(self, request, available_filters):
        """
        Extracts filter values from the request GET parameters based on available filter keys.
        """
        selected_filters = {}
        if not available_filters:
            return selected_filters

        for filter_key in available_filters.keys():
            values = request.GET.getlist(filter_key)
            if values:
                cleaned_values = [v for v in values if v]
                if cleaned_values:
                    selected_filters[filter_key] = cleaned_values
        return selected_filters

    @classmethod
    def get_results_data(cls, request, data_source_name, search_query, selected_filters):
        return controller.search_documents(
            data_source_name=data_source_name,
            query_text=search_query,
            filters=selected_filters,
            page=get_save_number(request.GET.get("page"), 1),
            page_size=get_save_number(request.GET.get("limit"), 50),
                source_fields=[
                "_id",
                "primary_location.source",
                "primary_location.doi",
                "publication_year",
                "biblio.volume",
                "biblio.issue",
                "biblio.first_page",
                "journal_metadata.issns",
                "journal_metadata.country",
                "title",
                "authorships",
                "primary_location.doi",
                "language",
                "type",
                "open_access.is_oa",
                "open_access.oa_status",
                "indexed_in",
                "locations.landing_page_url",
            ],
        )
