from .client import get_es_client
from . import data_sources
from . import query as query_builder
from . import parser as response_parser

FILTERS_CACHE = {}


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


def get_filters_data(data_source_name):
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

    aggs = query_builder.build_filters_aggs(field_settings)
    body = {"size": 0, "aggs": aggs}

    try:
        res = es.search(index=index_name, body=body)
        filters = response_parser.parse_filters_response(res)
        FILTERS_CACHE[index_name] = filters
        return filters, None
    except Exception:
        return None, "Error retrieving filters"
