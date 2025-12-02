from . import data_sources, data_sources_with_settings
from . import parser as response_parser
from . import query as query_builder
from .client import get_es_client

FILTERS_CACHE = {}


def get_mapped_filters(filters, field_settings):
    """
    Function to map the filters to the real field names.
    Args:
        filters: The filters to apply to the search.
        field_settings: The field settings to use to map the filters.
    Returns:
        A dictionary containing the mapped filters.
    """

    if filters:
        mapped_filters = {}
        for key, value in filters.items():
            if key in field_settings:
                real_field_name = field_settings[key].get("index_field_name")
                mapped_filters[real_field_name] = value
        return mapped_filters
    return None


def search_documents(
    data_source_name, query_text=None, filters=None, page=1, page_size=10, source_fields=None
):
    """
    Function to search documents in the database.
    Args:
        data_source_name: The name of the data source to search in.
        query_text: The text to search for.
        filters: The filters to apply to the search.
        page: The page number to return.
        page_size: The number of results per page.
        source_fields: The fields to return in the results.
    Returns:
        A dictionary containing the search results.
    """
    
    es = get_es_client()
    data_source = data_sources_with_settings.get_data_source(data_source_name)
    field_settings = data_sources_with_settings.get_field_settings(data_source_name)
    mapped_filters = get_mapped_filters(filters, field_settings)

    body = query_builder.build_document_search_body(
        query_text=query_text,
        filters=mapped_filters,
        page=page,
        page_size=page_size,
        source_fields=source_fields,
    )
    print(body)
    res = es.search(index=data_source.get("index_name"), body=body)
    parsed_results = response_parser.parse_document_search_response(res)
    return parsed_results


def search_as_you_type(data_source_name, query_text, field_name):
    es = get_es_client()
    data_source = data_sources_with_settings.get_data_source(data_source_name)
    fl_name = data_sources_with_settings.get_index_field_name_from_data_source(data_source_name, field_name)
    size = data_sources_with_settings.get_size_by_field_name(data_source_name, field_name)
    body = query_builder.build_search_as_you_type_body(
        field_name=fl_name,
        query=query_text,
        agg_size=size,
    )
    res = es.search(index=data_source.get("index_name"), body=body)
    parsed_results = response_parser.parse_search_item_response(res)
    return parsed_results


def get_search_item_results(q, data_source_name, field_name):
    """
    Orchestrates the search-as-you-type functionality.
    """
    es = get_es_client()
    if not es:
        return None, "Service unavailable"

    data_source = data_sources.DATA_SOURCES.get(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    field_settings = data_source.get("field_settings", {})
    fl_name = data_sources.get_index_field_name_from_data_source(
        data_source_name, field_name
    )
    supports_search_as_you_type = field_settings.get(field_name, {}).get(
        "filter", {}
    ).get("search_as_you_type", False)

    if supports_search_as_you_type:
        body = query_builder.build_search_as_you_type_body(fl_name, q)
    else:
        body = query_builder.build_term_search_body(fl_name, q)

    try:
        res = es.search(index=data_source.get("index_name"), body=body)
        parsed_results = response_parser.parse_search_item_response(res)
        return {"results": parsed_results}, None
    except Exception:
        return None, "Error executing or parsing search"


def get_filters_data(data_source_name, exclude_fields=None):
    """
    Orchestrates the retrieval of filter options.
    """
    es = get_es_client()
    if not es:
        return None, "Service unavailable"

    index_name = data_sources.get_index_name_from_data_source(data_source_name)
    if not index_name:
        return None, "Invalid index name"
        
    if index_name in FILTERS_CACHE:
        return FILTERS_CACHE[index_name], None

    field_settings = data_sources.get_field_settings(data_source_name)
    if not field_settings:
        return None, "Field settings not found"

    aggs = query_builder.build_filters_aggs(field_settings, exclude_fields)
    body = {"size": 0, "aggs": aggs}

    try:
        res = es.search(index=index_name, body=body)
        filters = response_parser.parse_filters_response(res)
        FILTERS_CACHE[index_name] = filters
        return filters, None
    except Exception:
        return None, "Error retrieving filters"
