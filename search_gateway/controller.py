from django.conf import settings

from . import filters_cache
from . import lookup
from . import parser as response_parser
from . import query as query_builder
from . import utils
from .client import get_opensearch_client
from .models import DataSource


def _resolve_data_source(identifier):
    return DataSource.resolve(identifier)


def _build_field_option_bodies(index_field_name, query_text, size):
    candidates = utils.get_index_field_candidates(index_field_name) or [index_field_name]
    cleaned_query = str(query_text or "").strip()
    bodies = []

    if not cleaned_query:
        for candidate_field in candidates:
            bodies.append(query_builder.build_unique_items_aggregation_body(candidate_field, aggregation_size=size))
        return bodies

    seen = set()
    for candidate_field in candidates:
        if candidate_field not in seen:
            bodies.append(query_builder.build_term_search_body(candidate_field, cleaned_query, aggregation_size=size))
            seen.add(candidate_field)

        contains_key = f"contains:{candidate_field}"
        if contains_key not in seen:
            bodies.append(
                query_builder.build_keyword_contains_search_body(
                    candidate_field,
                    cleaned_query,
                    aggregation_size=size,
                )
            )
            seen.add(contains_key)

    return bodies


def _search_data_source_field_options(es, data_source, settings_filter, query_text="", filters=None):
    field_settings = data_source.get_field_settings_dict()
    mapped_filters = utils.get_mapped_filters(filters or {}, field_settings)
    mapped_filters.pop(settings_filter.index_field_name, None)
    cleaned_query = str(query_text or "").strip()
    size = settings_filter.get_option_limit(default=20 if cleaned_query else 100)
    if cleaned_query:
        max_size_with_query = getattr(settings, "SEARCH_GATEWAY_SEARCH_ITEM_MAX_SIZE", 20)
        try:
            max_size_with_query = max(1, int(max_size_with_query))
        except (TypeError, ValueError):
            max_size_with_query = 20
        size = min(size, max_size_with_query)

    errors = []
    for body in _build_field_option_bodies(settings_filter.index_field_name, query_text, size):
        try:
            search_body = utils.apply_search_filters_to_body(body, mapped_filters)
            response = es.search(
                index=data_source.index_name,
                body=search_body,
                request_timeout=getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40),
            )
            parsed = response_parser.parse_search_item_response_with_transform(
                response,
                data_source,
                settings_filter.field_name,
            )
            return parsed, None
        except Exception as exc:
            errors.append(str(exc))

    if errors:
        return None, f"Error executing or parsing search: {errors[0]}"
    return [], None


def _enrich_options_with_lookup_labels(data_source_name, field_name, options, client=None):
    normalized_options = []
    values = []
    option_map = {}

    for option in options or []:
        value = str(option.get("key") or option.get("value") or "").strip()
        if not value:
            continue
        values.append(value)
        option_map[value] = dict(option)

    lookup_options, error = get_lookup_options_by_values(
        data_source_name,
        field_name,
        values,
        client=client,
    )
    if error or not lookup_options:
        return options, error

    lookup_map = {str(option.get("key") or ""): option for option in lookup_options if option.get("key")}
    for value in values:
        base_option = dict(option_map.get(value) or {})
        lookup_option = lookup_map.get(value) or {}
        base_option["label"] = lookup_option.get("label") or base_option.get("label") or value
        normalized_options.append(base_option)
    return normalized_options, None


def get_field_options(data_source_name, field_name, query_text="", client=None, filters=None):
    es = get_opensearch_client() if client is None else client
    if not es:
        return None, "Service unavailable"

    data_source = _resolve_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    settings_filter = data_source.get_field(field_name)
    if not settings_filter:
        return None, "Invalid field_name"

    lookup_config = settings_filter.get_lookup_config()
    if lookup_config:
        if (
            settings_filter.get_ui_setting("lookup_use_data_source_values")
            and not str(query_text or "").strip()
            and filters
        ):
            data_source_options, data_source_error = _search_data_source_field_options(
                es,
                data_source,
                settings_filter,
                query_text=query_text,
                filters=filters,
            )
            if data_source_error:
                return None, data_source_error
            return _enrich_options_with_lookup_labels(
                data_source.index_name,
                field_name,
                data_source_options,
                client=es,
            )
        try:
            return lookup.search_lookup_options(
                es,
                data_source,
                settings_filter,
                query_text=query_text,
                filters=filters,
            )
        except Exception as exc:
            return None, f"Error retrieving lookup options: {exc}"

    if not settings_filter.index_field_name:
        return [], None

    return _search_data_source_field_options(
        es,
        data_source,
        settings_filter,
        query_text=query_text,
        filters=filters,
    )


def get_lookup_options_by_values(data_source_name, field_name, values, client=None):
    es = get_opensearch_client() if client is None else client
    if not es:
        return None, "Service unavailable"

    data_source = _resolve_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    settings_filter = data_source.get_field(field_name)
    if not settings_filter:
        return None, "Invalid field_name"

    lookup_config = settings_filter.get_lookup_config()
    if not lookup_config:
        return None, "Lookup not configured"

    try:
        return lookup.search_lookup_options_by_values(es, data_source, settings_filter, values)
    except Exception as exc:
        return None, f"Error retrieving lookup options: {exc}"


def search_as_you_type(data_source_name, query_text, field_name, client=None):
    results, _error = get_field_options(
        data_source_name,
        field_name,
        query_text=query_text,
        client=client,
    )
    return results or []


def search_item(q, data_source_name, field_name, client=None, filters=None):
    results, error = get_field_options(
        data_source_name,
        field_name,
        query_text=q,
        client=client,
        filters=filters,
    )
    if error:
        return None, error
    return {"results": results or []}, None


def get_filters_data(
    data_source_name,
    exclude_fields=None,
    include_fields=None,
    force_refresh=False,
    filters=None,
    client=None,
):
    es = get_opensearch_client() if client is None else client
    if not es:
        return None, "Service unavailable"

    data_source = _resolve_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    index_name = data_source.index_name
    field_settings = data_source.get_field_settings_dict(
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    field_settings = {
        field_name: field_info
        for field_name, field_info in field_settings.items()
        if field_info.get("kind") != "control"
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
        response = es.search(
            index=index_name,
            body=body,
            request_timeout=getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40),
        )

        filters_data = response_parser.parse_filters_response_with_transform(
            response,
            data_source,
        )
        filters_cache.store_filters_cache(cache_key, filters_data)
        return filters_data, None
    except Exception as exc:
        return None, f"Error retrieving filters: {exc}"
