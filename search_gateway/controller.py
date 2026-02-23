import json
import time

from . import data_sources_with_settings
from . import parser as response_parser
from . import query as query_builder
from .client import get_es_client, get_opensearch_client

from .models import DataSource

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
    es = _get_search_client_for_data_source(data_source_name, client=client)
    data_source = DataSource.get_by_index_name(index_name=data_source_name)
    if not data_source and not data_source.settings_filters.get_by_field_name(field_name=field_name):
        return []

    settings_filter = data_source.settings_filters.get_by_field_name(field_name=field_name)
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
    es = _get_search_client_for_data_source(data_source_name, client=client)
    if not es:
        return None, "Service unavailable"

    data_source = data_sources_with_settings.get_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    field_settings = data_source.get("field_settings", {})
    field_data = data_sources_with_settings.get_data_by_field_name(
        data_source_name, field_name
    ) or {}
    fl_name = data_sources_with_settings.get_index_field_name_from_data_source(
        data_source_name, field_name
    )
    field_autocomplete = field_data.get("field_autocomplete")
    supports_search_as_you_type = bool(
        data_sources_with_settings.field_supports_search_as_you_type(
            data_source_name, field_name
        )
        and field_autocomplete
    )
    size = data_sources_with_settings.get_size_by_field_name(data_source_name, field_name)
    mapped_filters = get_mapped_filters(filters or {}, field_settings)

    if data_source_name == "journal_metrics" and field_name == "category_id":
        category_level_field = (
            field_settings.get("category_level", {}) or {}
        ).get("index_field_name")
        if category_level_field:
            mapped_filters[category_level_field] = _normalize_journal_metrics_category_level(
                (filters or {}).get("category_level")
            )

    if fl_name in mapped_filters:
        mapped_filters.pop(fl_name, None)

    journal_metrics_keyword_contains_fields = {
        "journal_title",
        "journal_issn",
        "publisher_name",
        "category_id",
    }

    if data_source_name == "journal_metrics" and field_name in journal_metrics_keyword_contains_fields:
        bodies = [query_builder.build_keyword_contains_search_body(fl_name, q)]
    elif supports_search_as_you_type:
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

        # Fallbacks for keyword/non-text fields (e.g. primary_source_issns) that
        # may fail with match_phrase_prefix depending on mapping.
        for candidate_field in _get_index_field_candidates(fl_name):
            bodies.append(query_builder.build_keyword_contains_search_body(candidate_field, q))
            if candidate_field != fl_name:
                bodies.append(query_builder.build_term_search_body(candidate_field, q))

    search_errors = []
    for body in bodies:
        try:
            search_body = _apply_search_filters_to_body(body, mapped_filters)
            res = es.search(index=data_source.get("index_name"), body=search_body)
            parsed_results = response_parser.parse_search_item_response(res, data_source_name, field_name)
            return {"results": parsed_results}, None
        except Exception as exc:
            search_errors.append(str(exc))

    if search_errors:
        return None, f"Error executing or parsing search: {search_errors[0]}"
    return None, "Error executing or parsing search"


def _parse_filters_cache_entry(cache_entry):
    if isinstance(cache_entry, dict) and "data" in cache_entry and "cached_at" in cache_entry:
        return cache_entry.get("data"), cache_entry.get("cached_at")
    return cache_entry, None


def _normalize_filters_for_cache(filters):
    if not filters:
        return ()

    normalized = []
    for key, value in filters.items():
        if isinstance(value, list):
            normalized.append((key, tuple(sorted(str(v) for v in value if v not in (None, "")))))
        else:
            normalized.append((key, str(value)))
    return tuple(sorted(normalized))


def _build_filters_body(aggs, mapped_filters=None):
    body = {"size": 0, "aggs": aggs}
    if mapped_filters:
        body["query"] = {"bool": {"filter": query_builder.query_filters(mapped_filters)}}
    return body


def _store_filters_cache(cache_key, filters_data):
    FILTERS_CACHE[cache_key] = {
        "data": filters_data,
        "cached_at": time.monotonic(),
    }


def _field_settings_cache_fingerprint(field_settings):
    if not field_settings:
        return ()

    return tuple(
        sorted(
            (
                field_name,
                (field_info or {}).get("index_field_name"),
                json.dumps(((field_info or {}).get("filter") or {}), sort_keys=True, default=str),
            )
            for field_name, field_info in field_settings.items()
        )
    )


def _get_index_field_candidates(index_field_name):
    if not index_field_name:
        return []

    if index_field_name.endswith(".keyword"):
        candidates = [index_field_name, index_field_name[:-8]]
    else:
        candidates = [index_field_name, f"{index_field_name}.keyword"]

    seen = set()
    unique_candidates = []
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)
    return unique_candidates


def _get_filters_data_with_field_fallback(
    es,
    index_name,
    data_source_name,
    field_settings,
    mapped_filters,
    exclude_fields,
):
    partial_filters = {}
    field_errors = {}

    for form_field_name, field_info in field_settings.items():
        if form_field_name in exclude_fields:
            continue
        if field_info.get("filter", {}).get("use") is False:
            continue

        configured_index_field = field_info.get("index_field_name")
        if not configured_index_field:
            continue

        search_filters = {
            key: value
            for key, value in (mapped_filters or {}).items()
            if key != configured_index_field
        }

        last_error = None
        success = False

        for candidate_field in _get_index_field_candidates(configured_index_field):
            single_field_settings = {
                form_field_name: {
                    **field_info,
                    "index_field_name": candidate_field,
                }
            }
            aggs = query_builder.build_filters_aggs(single_field_settings, exclude_fields=[])
            if not aggs:
                continue

            body = _build_filters_body(aggs, mapped_filters=search_filters)

            try:
                res = es.search(index=index_name, body=body)
                parsed = response_parser.parse_filters_response(res, data_source_name)
                partial_filters[form_field_name] = parsed.get(form_field_name, [])
                success = True
                break
            except Exception as exc:
                last_error = exc

        if not success:
            partial_filters[form_field_name] = []
            if last_error:
                field_errors[form_field_name] = str(last_error)

    return partial_filters, field_errors


def get_filters_data(
    data_source_name,
    client=None,
    exclude_fields=None,
    include_fields=None,
    force_refresh=False,
    filters=None,
):
    """
    Get available filter options from Elasticsearch.
    
    Args:
        data_source_name: Name of the data source.
        exclude_fields: List of fields to exclude.
    
    Returns:
        Tuple of (filters_dict, error_message).
    """
    es = _get_search_client_for_data_source(data_source_name, client=client)
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

    cache_key = (
        data_source_name,
        index_name,
        tuple(sorted(exclude_fields)),
        tuple(sorted(include_fields)),
        _normalize_filters_for_cache(filters),
        _field_settings_cache_fingerprint(field_settings),
    )
    if not force_refresh and cache_key in FILTERS_CACHE:
        cached_data, cached_at = _parse_filters_cache_entry(FILTERS_CACHE[cache_key])
        if cached_at is None or (time.monotonic() - cached_at) <= FILTERS_CACHE_TTL_SECONDS:
            return cached_data, None

    aggs = query_builder.build_filters_aggs(field_settings, exclude_fields)
    body = {"size": 0, "aggs": aggs}
    mapped_filters = get_mapped_filters(filters or {}, field_settings)
    if mapped_filters:
        body["query"] = {"bool": {"filter": query_builder.query_filters(mapped_filters)}}

    try:
        res = es.search(index=index_name, body=body)
        filters_data = response_parser.parse_filters_response(res, data_source_name)
        _store_filters_cache(cache_key, filters_data)
        return filters_data, None
    except Exception as exc:
        fallback_filters, fallback_errors = _get_filters_data_with_field_fallback(
            es=es,
            index_name=index_name,
            data_source_name=data_source_name,
            field_settings=field_settings,
            mapped_filters=mapped_filters,
            exclude_fields=exclude_fields,
        )
        if fallback_filters:
            _store_filters_cache(cache_key, fallback_filters)
            return fallback_filters, None

        if fallback_errors:
            details = "; ".join(
                f"{field_name}: {error}" for field_name, error in sorted(fallback_errors.items())
            )
            return None, f"Error retrieving filters: {exc}. Fallback errors: {details}"

        return None, f"Error retrieving filters: {exc}"
