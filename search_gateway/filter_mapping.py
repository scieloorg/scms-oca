from .query import query_filters
from .transforms import coerce_boolean


def _normalize_boolean_value(value):
    return coerce_boolean(value)


def _build_year_range_values(start_value, end_value):
    try:
        start_year = int(start_value) if start_value not in (None, "") else None
    except (TypeError, ValueError):
        start_year = None

    try:
        end_year = int(end_value) if end_value not in (None, "") else None
    except (TypeError, ValueError):
        end_year = None

    if start_year is None and end_year is None:
        return []

    if start_year is None:
        start_year = end_year
    if end_year is None:
        end_year = start_year

    if start_year > end_year:
        start_year, end_year = end_year, start_year

    return list(range(start_year, end_year + 1))


def _map_transformed_filter(field_name, field_info, filters):
    transform = field_info.get("filter", {}).get("transform", {}) or {}
    transform_type = transform.get("type")
    real_field_name = field_info.get("index_field_name")
    if not transform_type or not real_field_name:
        return None, set()

    if transform_type == "boolean":
        raw_value = filters.get(field_name)
        handled_fields = {field_name}
        if isinstance(raw_value, list):
            normalized_values = [_normalize_boolean_value(value) for value in raw_value]
            normalized_values = [value for value in normalized_values if value is not None]
            if normalized_values:
                return (real_field_name, normalized_values), handled_fields
            return None, handled_fields

        normalized_value = _normalize_boolean_value(raw_value)
        if normalized_value is not None:
            return (real_field_name, normalized_value), handled_fields
        return None, handled_fields

    if transform_type != "year_range":
        return None, set()

    source_names = list(transform.get("sources") or [])
    handled_fields = set(source_names)
    if field_name in filters:
        handled_fields.add(field_name)
    if len(source_names) != 2:
        return None, handled_fields

    year_values = _build_year_range_values(
        filters.get(source_names[0]),
        filters.get(source_names[1]),
    )
    if year_values:
        return (real_field_name, year_values), handled_fields
    return None, handled_fields


def apply_search_filters_to_body(body, mapped_filters):
    if not mapped_filters:
        return body

    original_query = body.get("query", {"match_all": {}})

    body_with_filters = dict(body)

    body_with_filters["query"] = {
        "bool": {
            "must": [original_query],
                "filter": query_filters(mapped_filters),
        }
    }

    return body_with_filters


def get_mapped_filters(filters, field_settings):
    """
    Map form filter names to Elasticsearch field names.

    Args:
        filters: Dict of filters with form field names.
        field_settings: Field settings from data source configuration.

    Returns:
        Dict with Elasticsearch field names as keys.
    """
    if not filters:
        return {}

    mapped_filters = {}
    handled_fields = set()

    for field_name, field_info in field_settings.items():
        if field_info.get("kind") == "control":
            continue
        mapped_filter, transformed_fields = _map_transformed_filter(field_name, field_info, filters)
        handled_fields.update(transformed_fields)
        if mapped_filter:
            real_field_name, value = mapped_filter
            mapped_filters[real_field_name] = value

    for key, value in filters.items():
        if key in handled_fields:
            continue
        if key not in field_settings:
            continue
        field_config = field_settings[key]
        if field_config.get("kind") == "control":
            continue
        real_field_name = field_config.get("index_field_name")
        if not real_field_name or value in (None, "", []):
            continue
        mapped_filters[real_field_name] = value

    return mapped_filters


def get_index_field_candidates(index_field_name):
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


def build_filters_body(aggs, mapped_filters=None):
    body = {"size": 0, "aggs": aggs}

    if mapped_filters:
        body["query"] = {"bool": {"filter": query_filters(mapped_filters)}}

    return body
