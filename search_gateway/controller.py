from . import data_sources_with_settings
from . import parser as response_parser
from . import query as query_builder
from .client import get_es_client, get_opensearch_client
import json
import time

FILTERS_CACHE = {}
FILTERS_CACHE_TTL_SECONDS = 300
OPENSEARCH_DATA_SOURCES = {
    "world",
    "brazil",
    "scielo",
    "social",
    "journal_metrics",
}

DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL = "field"
VALID_JOURNAL_METRICS_CATEGORY_LEVELS = {"domain", "field", "subfield", "topic"}


def _normalize_journal_metrics_category_level(value):
    normalized = str(value or "").strip().lower()
    if not normalized:
        return DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL
    if normalized not in VALID_JOURNAL_METRICS_CATEGORY_LEVELS:
        return DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL
    return normalized


def _get_search_client_for_data_source(data_source_name, client=None):
    if client:
        return client
    if data_source_name in OPENSEARCH_DATA_SOURCES:
        return get_opensearch_client()
    return get_es_client()


def _apply_search_filters_to_body(body, mapped_filters):
    if not mapped_filters:
        return body

    original_query = body.get("query", {"match_all": {}})
    body_with_filters = dict(body)
    body_with_filters["query"] = {
        "bool": {
            "must": [original_query],
            "filter": query_builder.query_filters(mapped_filters),
        }
    }
    return body_with_filters

def get_mapped_filters(filters, field_settings):
    """
    Map form filter names to Elasticsearch field namclient.
    
    Args:
        filters: Dict of filters with form field namclient.
        field_settings: Field settings from data source configuration.
    
    Returns:
        Dict with Elasticsearch field names as keys.
    """
    if not filters:
        return {}
    
    mapped_filters = {}
    for key, value in filters.items():
        if key in field_settings:
            real_field_name = field_settings[key].get("index_field_name")
            mapped_filters[real_field_name] = value
    return mapped_filters


def search_documents(
    data_source_name,
    query_text=None,
    filters=None,
    page=1,
    page_size=10,
    source_fields=None,
    client=None
):
    """
    Search documents in Elasticsearch.
    
    Args:
        data_source_name: Name of the data source.
        query_text: Text to search for.
        filters: Dict of filters to apply.
        page: Page number (1-based).
        page_size: Number of results per page.
        source_fields: Fields to include in results.
    
    Returns:
        Dict with 'search_results' and 'total_results'.
    """
    es = client or get_es_client()
    data_source = data_sources_with_settings.get_data_source(data_source_name)
    field_settings = data_source.get("field_settings", {})
    index_name = data_source.get("index_name")
    mapped_filters = get_mapped_filters(filters, field_settings)
    
    body = query_builder.build_document_search_body(
        query_text=query_text,
        filters=mapped_filters,
        page=page,
        page_size=page_size,
        source_fields=source_fields,
        data_source_name=data_source_name,
    )
    
    res = es.search(index=index_name, body=body)
    return response_parser.parse_document_search_response(res)


def search_as_you_type(data_source_name, query_text, field_name, client=None):
    """
    Perform search-as-you-type query for autocomplete.
    
    Args:
        data_source_name: Name of the data source.
        query_text: Text to search for.
        field_name: Field to search in.
    
    Returns:
        List of matching items.
    """
    es = client or get_es_client()
    data_source = data_sources_with_settings.get_data_source(data_source_name)
    fl_name = data_sources_with_settings.get_index_field_name_from_data_source(data_source_name, field_name)
    size = data_sources_with_settings.get_size_by_field_name(data_source_name, field_name)
    field_autocomplete = data_sources_with_settings.get_field_autocomplete_from_data_source(data_source_name, field_name)
    body = query_builder.build_search_as_you_type_body(
        field_name=fl_name,
        query=query_text,
        agg_size=size,
        field_autocomplete=field_autocomplete
    )

    res = es.search(index=data_source.get("index_name"), body=body)
    return response_parser.parse_search_item_response(res, data_source_name, field_name)


def search_item(q, data_source_name, field_name, client=None):
    """
    Search
    
    Args:
        q: Query text.
        data_source_name: Name of the data source.
        field_name: Field to search in.
    
    Returns:
        Tuple of (results_dict, error_message).
    """
    es = client or get_es_client()
    if not es:
        return None, "Service unavailable"

    data_source = data_sources_with_settings.get_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    field_settings = data_source.get("field_settings", {})
    fl_name = data_sources_with_settings.get_index_field_name_from_data_source(
        data_source_name, field_name
    )
    supports_search_as_you_type = field_settings.get(field_name, {}).get(
        "filter", {}
    ).get("search_as_you_type", False)

    if supports_search_as_you_type:
        body = query_builder.build_search_as_you_type_body(fl_name, q, add_keyword_term=True)
    else:
        body = query_builder.build_term_search_body(fl_name, q)

    try:
        res = es.search(index=data_source.get("index_name"), body=body)
        parsed_results = response_parser.parse_search_item_response(res, data_source_name, field_name)
        return {"results": parsed_results}, None
    except Exception:
        return None, "Error executing or parsing search"


def get_filters_data(data_source_name, client=None, exclude_fields=None):
    """
    Get available filter options from Elasticsearch.
    
    Args:
        data_source_name: Name of the data source.
        exclude_fields: List of fields to exclude.
    
    Returns:
        Tuple of (filters_dict, error_message).
    """
    es = client or get_es_client()
    if not es:
        return None, "Service unavailable"

    index_name = data_sources_with_settings.get_index_name_from_data_source(data_source_name)
    if not index_name:
        return None, "Invalid index name"
        
    if index_name in FILTERS_CACHE:
        return FILTERS_CACHE[index_name], None

    field_settings = data_sources_with_settings.get_field_settings(data_source_name)
    if not field_settings:
        return None, "Field settings not found"

    aggs = query_builder.build_filters_aggs(field_settings, exclude_fields)
    body = {"size": 0, "aggs": aggs}

    try:
        res = es.search(index=index_name, body=body)
        filters = response_parser.parse_filters_response(res, data_source_name)
        FILTERS_CACHE[index_name] = filters
        return filters, None
    except Exception:
        return None, "Error retrieving filters"
