from django.conf import settings

from . import data_sources_with_settings
from . import filters_cache
from . import utils
from . import parser as response_parser
from . import query as query_builder

from .client import get_opensearch_client
from .models import DataSource


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
    es = get_opensearch_client() if client is None else client
    data_source = DataSource.get_by_index_name(index_name=data_source_name)
    if not data_source:
        return []

    settings_filter = data_source.settings_filters.get_by_field_name(field_name=field_name)
    if not settings_filter:
        return []

    fl_name = settings_filter.index_field_name
    field_autocomplete = settings_filter.field_autocomplete
    size = (settings_filter.filter or {}).get("size", 20)
    body = query_builder.build_search_as_you_type_body(
        field_name=fl_name,
        field_autocomplete=field_autocomplete,
        query=query_text,
        agg_size=size,
    )
    res = es.search(index=data_source.index_name, body=body)
    return response_parser.parse_search_item_response_with_transform(res, data_source, field_name)


def search_item(q, data_source_name, field_name, client=None, filters=None):
    """
    Search
    
    Args:
        q: Query text.
        data_source_name: Name of the data source.
        field_name: Field to search in.
    
    Returns:
        Tuple of (results_dict, error_message).
    """
    es = get_opensearch_client() if client is None else client
    if not es:
        return None, "Service unavailable"

    data_source = data_sources_with_settings.get_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    field_settings = data_source.get("field_settings", {})
    field_data = data_sources_with_settings.get_data_by_field_name(data_source_name, field_name) or {}
    fl_name = data_sources_with_settings.get_index_field_name_from_data_source(data_source_name, field_name)
    field_autocomplete = field_data.get("field_autocomplete")
    supports_search_as_you_type = bool(data_sources_with_settings.field_supports_search_as_you_type(data_source_name, field_name) and field_autocomplete)
    size = data_sources_with_settings.get_size_by_field_name(data_source_name, field_name)
    mapped_filters = utils.get_mapped_filters(filters or {}, field_settings)

    if fl_name in mapped_filters:
        mapped_filters.pop(fl_name, None)

    if supports_search_as_you_type:
        bodies = [
            query_builder.build_search_as_you_type_body(
                field_name=fl_name,
                field_autocomplete=field_autocomplete,
                query=q,
                agg_size=size,
            )
        ]
    else:
        bodies = [query_builder.build_term_search_body(fl_name, q)]

        for candidate_field in utils.get_index_field_candidates(fl_name):
            bodies.append(query_builder.build_keyword_contains_search_body(candidate_field, q))

            if candidate_field != fl_name:
                bodies.append(query_builder.build_term_search_body(candidate_field, q))

    search_errors = []
    for body in bodies:
        try:
            search_body = utils.apply_search_filters_to_body(body, mapped_filters)
            res = es.search(index=data_source.get("index_name"), body=search_body)
            parsed_results = response_parser.parse_search_item_response(res, data_source_name, field_name)
        
            return {"results": parsed_results}, None
        
        except Exception as exc:
            search_errors.append(str(exc))

    if search_errors:
        return None, f"Error executing or parsing search: {search_errors[0]}"
    
    return None, "Error executing or parsing search"


def get_filters_data(
    data_source_name,
    exclude_fields=None,
    include_fields=None,
    force_refresh=False,
    filters=None,
    client=None,
):
    """
    Get available filter options from Elasticsearch.
    
    Args:
        data_source_name: Name of the data source.
        exclude_fields: List of fields to exclude.
        include_fields: List of fields to include.
        force_refresh: Whether to force refresh the cache.
        filters: Additional filters to apply.
    
    Returns:
        Tuple of (filters_dict, error_message).
    """
    es = get_opensearch_client() if client is None else client
    if not es:
        return None, "Service unavailable"

    index_name = data_sources_with_settings.get_index_name_from_data_source(data_source_name)
    if not index_name:
        return None, "Invalid index name"

    field_settings = data_sources_with_settings.get_field_settings(data_source_name)
    if not field_settings:
        return None, "Field settings not found"

    exclude_fields = exclude_fields or []
    include_fields = include_fields or []
    if include_fields:
        field_settings = {
            field_name: field_info
            for field_name, field_info in field_settings.items()
            if field_name in include_fields
        }
        if not field_settings:
            return {}, None

    cache_key = filters_cache.build_filters_cache_key(
        data_source_name=data_source_name,
        index_name=index_name,
        exclude_fields=exclude_fields,
        include_fields=include_fields,
        filters=filters,
        field_settings=field_settings,
    )
    
    cached_data = filters_cache.get_cached_filters(cache_key, force_refresh=force_refresh)
    if cached_data is not None:
        return cached_data, None

    aggs = query_builder.build_filters_aggs(field_settings, exclude_fields)
    mapped_filters = utils.get_mapped_filters(filters or {}, field_settings)
    body = utils.build_filters_body(aggs, mapped_filters=mapped_filters)

    try:
        res = es.search(
            index=index_name,
            body=body,
            request_timeout=getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40),
        )

        filters_data = response_parser.parse_filters_response(res, data_source_name)
        filters_cache.store_filters_cache(cache_key, filters_data)

        return filters_data, None

    except Exception as exc:
        return None, f"Error retrieving filters: {exc}"
