from django.conf import settings

from .option_normalization import (
    TRUE_VALUES,
    normalize_boolean,
    normalize_filter_default_value,
)

DEFAULT_FILTER_SUFFIXES = ("_operator", "_bool_not")
FILTER_SUFFIXES = tuple(getattr(settings, "SEARCH_GATEWAY_FILTER_SUFFIXES", DEFAULT_FILTER_SUFFIXES))

DEFAULT_EXCLUDED_QUERY_KEYS = frozenset(
    {
        "csrfmiddlewaretoken",
        "search",
        "advanced_search",
        "search_clauses",
        "page",
        "limit",
        "sort",
        "index_name",
        "data_source",
        "form",
        "include_form",
        "refresh",
        "fields",
        "clear_defaults",
    }
)
EXCLUDED_QUERY_KEYS = frozenset(
    getattr(settings, "SEARCH_GATEWAY_EXCLUDED_QUERY_KEYS", tuple(DEFAULT_EXCLUDED_QUERY_KEYS))
)

CLEAR_DEFAULTS_QUERY_PARAM = getattr(settings, "SEARCH_GATEWAY_CLEAR_DEFAULTS_QUERY_PARAM", "clear_defaults")
CLEAR_DEFAULTS_INTERNAL_FLAG = "__clear_defaults__"
TRUTHY_FLAG_VALUES = TRUE_VALUES


def _should_skip_default_filters(source):
    value = str((source or {}).get(CLEAR_DEFAULTS_QUERY_PARAM) or "").strip().lower()
    return value in TRUTHY_FLAG_VALUES


def _extract_non_empty_values(source, key):
    values = [value for value in source.getlist(key) if value not in (None, "")]
    return values if values else []


def _apply_default_filters(applied_filters, data_source, form_key=None):
    resolved_filters = dict(applied_filters or {})

    for field in data_source.get_ordered_fields(form_key=form_key):
        default_value = field.default_value
        if default_value in (None, "", {}, []):
            continue

        source_names = field.transform_sources
        if source_names:
            if any(resolved_filters.get(source_name) not in (None, "", []) for source_name in source_names):
                continue
            if not isinstance(default_value, dict):
                continue

            if len(source_names) >= 1 and default_value.get("start") not in (None, ""):
                resolved_filters[source_names[0]] = str(default_value.get("start"))
            if len(source_names) >= 2 and default_value.get("end") not in (None, ""):
                resolved_filters[source_names[1]] = str(default_value.get("end"))
            continue

        if field.field_name in resolved_filters:
            continue

        normalized_default_value = normalize_filter_default_value(default_value)
        if normalized_default_value is not None:
            resolved_filters[field.field_name] = normalized_default_value

    return resolved_filters


def _extract_filters_from_source(source, excluded_keys=None, allowed_keys=None):
    excluded_keys = set(excluded_keys or [])
    allowed_keys = set(allowed_keys or [])
    extracted_filters = {}

    for key in source.keys():
        if key in excluded_keys:
            continue
        if allowed_keys and key not in allowed_keys:
            continue

        values = _extract_non_empty_values(source, key)
        if not values:
            continue
        extracted_filters[key] = values if len(values) > 1 else values[0]

    return extracted_filters


def _build_allowed_applied_filter_keys(data_source, form_key=None):
    allowed_keys = set()
    for field in data_source.get_ordered_fields(form_key=form_key):
        allowed_keys.add(field.field_name)
        allowed_keys.update(field.transform_sources)
        if field.supports_query_operator:
            allowed_keys.update({field.operator_field_name, field.bool_not_field_name})
    return allowed_keys


def extract_applied_filters_from_source(source, data_source, form_key=None, extra_excluded_keys=None):
    extra_excluded_keys = set(extra_excluded_keys or [])
    excluded_keys = set(EXCLUDED_QUERY_KEYS) | extra_excluded_keys
    allowed_keys = _build_allowed_applied_filter_keys(data_source, form_key=form_key)
    return _extract_filters_from_source(
        source,
        excluded_keys=excluded_keys,
        allowed_keys=allowed_keys,
    )


def apply_default_filters(applied_filters, data_source, form_key=None, skip_defaults=False):
    resolved_filters = dict(applied_filters or {})
    if skip_defaults:
        resolved_filters[CLEAR_DEFAULTS_INTERNAL_FLAG] = True
        return resolved_filters
    return _apply_default_filters(resolved_filters, data_source, form_key=form_key)


def extract_requested_filters(source, excluded_keys=None, allowed_keys=None):
    return _extract_filters_from_source(
        source,
        excluded_keys=excluded_keys,
        allowed_keys=allowed_keys,
    )


def extract_selected_filters(source, data_source, available_filters=None):
    selected_filters = {}
    field_settings = data_source.field_settings_dict
    filter_keys = available_filters.keys() if available_filters else field_settings.keys()

    for filter_key in filter_keys:
        cleaned_values = _extract_non_empty_values(source, filter_key)
        if not cleaned_values:
            continue

        field_config = field_settings.get(filter_key, {})
        transform_type = (field_config.get("filter") or {}).get("transform", {}).get("type")
        if transform_type == "boolean":
            transformed_value = normalize_boolean(cleaned_values)
            if transformed_value:
                selected_filters[filter_key] = transformed_value
            continue

        selected_filters[filter_key] = cleaned_values

    return selected_filters


def extract_applied_filters(source, data_source, form_key=None, extra_excluded_keys=None):
    extracted_filters = extract_applied_filters_from_source(
        source,
        data_source,
        form_key=form_key,
        extra_excluded_keys=extra_excluded_keys,
    )
    return apply_default_filters(
        extracted_filters,
        data_source,
        form_key=form_key,
        skip_defaults=_should_skip_default_filters(source),
    )


def build_option_filters(applied_filters, field, excluded_filter_names=None):
    excluded_names = set(excluded_filter_names or [])
    excluded_names.update({field.field_name, field.operator_field_name, field.bool_not_field_name})

    return normalize_option_filters(
        applied_filters,
        excluded_filter_names=excluded_names,
    )


def normalize_option_filters(applied_filters, excluded_filter_names=None):
    excluded_filter_names = set(excluded_filter_names or [])
    return {
        key: value
        for key, value in (applied_filters or {}).items()
        if not str(key).startswith("__")
        and key not in excluded_filter_names
        and not key.endswith(FILTER_SUFFIXES)
        and value not in (None, "", [])
    }
