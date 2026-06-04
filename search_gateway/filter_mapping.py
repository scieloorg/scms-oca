from .query import query_filters
from .option_normalization import normalize_boolean


DEFAULT_YEAR_MIN = 1800
DEFAULT_YEAR_MAX = 2100


def _parse_number_bound(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _parse_numeric_value(value, *, min_value=None, max_value=None):
    try:
        numeric_value = int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None

    if numeric_value is None:
        return None
    if min_value is not None and numeric_value < min_value:
        return None
    if max_value is not None and numeric_value > max_value:
        return None
    return numeric_value


def _build_numeric_range_value(start_value, end_value, *, min_value=None, max_value=None):
    start_number = _parse_numeric_value(
        start_value,
        min_value=min_value,
        max_value=max_value,
    )
    end_number = _parse_numeric_value(
        end_value,
        min_value=min_value,
        max_value=max_value,
    )

    if start_number is None and end_number is None:
        return {}

    if start_number is not None and end_number is not None and start_number > end_number:
        start_number, end_number = end_number, start_number

    range_value = {}
    if start_number is not None:
        range_value["gte"] = start_number
    if end_number is not None:
        range_value["lte"] = end_number
    return range_value


def _parse_year_value(value, *, min_year=None, max_year=None):
    try:
        year = int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None

    if year is None:
        return None
    min_year = DEFAULT_YEAR_MIN if min_year is None else min_year
    max_year = DEFAULT_YEAR_MAX if max_year is None else max_year
    if len(str(abs(year))) != 4:
        return None
    if min_year is not None and year < min_year:
        return None
    if max_year is not None and year > max_year:
        return None
    return year


def _parse_year_bound(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _build_year_range_values(start_value, end_value, *, min_year=None, max_year=None):
    start_year = _parse_year_value(start_value, min_year=min_year, max_year=max_year)
    end_year = _parse_year_value(end_value, min_year=min_year, max_year=max_year)

    if start_year is None and end_year is None:
        return []

    effective_min = DEFAULT_YEAR_MIN if min_year is None else min_year
    effective_max = DEFAULT_YEAR_MAX if max_year is None else max_year

    if start_year is None:
        start_year = effective_min
    if end_year is None:
        end_year = effective_max

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
            normalized_values = [normalize_boolean(value) for value in raw_value]
            normalized_values = [value for value in normalized_values if value is not None]
            if normalized_values:
                return (real_field_name, normalized_values), handled_fields
            return None, handled_fields

        normalized_value = normalize_boolean(raw_value)
        if normalized_value is not None:
            return (real_field_name, normalized_value), handled_fields
        return None, handled_fields

    if transform_type not in {"year_range", "numeric_range"}:
        return None, set()

    source_names = list(transform.get("sources") or [])
    handled_fields = set(source_names)
    if field_name in filters:
        handled_fields.add(field_name)
    if len(source_names) != 2:
        return None, handled_fields

    settings = field_info.get("settings") or {}
    if transform_type == "numeric_range":
        min_value = _parse_number_bound(settings.get("min"))
        max_value = _parse_number_bound(settings.get("max"))
        numeric_range = _build_numeric_range_value(
            filters.get(source_names[0]),
            filters.get(source_names[1]),
            min_value=min_value,
            max_value=max_value,
        )
        if numeric_range:
            return (real_field_name, numeric_range), handled_fields
        return None, handled_fields

    min_year = _parse_year_bound(settings.get("min"))
    max_year = _parse_year_bound(settings.get("max"))

    year_values = _build_year_range_values(
        filters.get(source_names[0]),
        filters.get(source_names[1]),
        min_year=min_year,
        max_year=max_year,
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
        return [index_field_name, index_field_name[:-8]]
    return [index_field_name, f"{index_field_name}.keyword"]


def build_filters_body(aggs, mapped_filters=None):
    body = {"size": 0, "aggs": aggs}

    if mapped_filters:
        body["query"] = {"bool": {"filter": query_filters(mapped_filters)}}

    return body
