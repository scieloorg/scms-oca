from django.conf import settings

from . import transforms


DEFAULT_FILTER_SUFFIXES = ("_operator", "_bool_not")
FILTER_SUFFIXES = tuple(getattr(settings, "SEARCH_GATEWAY_FILTER_SUFFIXES", DEFAULT_FILTER_SUFFIXES))

DEFAULT_EXCLUDED_QUERY_KEYS = frozenset(
    {
        "csrfmiddlewaretoken",
        "search",
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
TRUTHY_FLAG_VALUES = {"1", "true", "yes", "y", "sim", "on"}


def _should_skip_default_filters(source):
    if not source:
        return False
    value = str(source.get(CLEAR_DEFAULTS_QUERY_PARAM) or "").strip().lower()
    return value in TRUTHY_FLAG_VALUES


def _apply_default_filters(applied_filters, data_source, form_key=None):
    resolved_filters = dict(applied_filters or {})

    for field in data_source.get_ordered_fields(form_key=form_key):
        default_value = field.get_default_value(default=None)
        if default_value in (None, "", {}, []):
            continue

        source_names = field.get_transform_sources()
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

        if isinstance(default_value, (list, tuple)):
            values = [str(value) for value in default_value if value not in (None, "")]
            if not values:
                continue
            resolved_filters[field.field_name] = values if len(values) > 1 else values[0]
            continue

        resolved_filters[field.field_name] = str(default_value)

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

        values = [value for value in source.getlist(key) if value not in (None, "")]
        if not values:
            continue
        extracted_filters[key] = values if len(values) > 1 else values[0]

    return extracted_filters


def _build_allowed_applied_filter_keys(data_source, form_key=None):
    field_names = set()
    transform_source_names = set()

    for field in data_source.get_ordered_fields(form_key=form_key):
        field_names.add(field.field_name)
        transform_source_names.update(field.get_transform_sources())
        if field.supports_query_operator():
            field_names.add(field.get_operator_field_name())
            field_names.add(field.get_bool_not_field_name())

    return field_names | transform_source_names


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
    field_settings = data_source.get_field_settings_dict()
    filter_keys = available_filters.keys() if available_filters else field_settings.keys()

    for filter_key in filter_keys:
        values = source.getlist(filter_key)
        if not values:
            continue

        cleaned_values = [value for value in values if value]
        if not cleaned_values:
            continue

        field_config = field_settings.get(filter_key, {})
        transform_type = (field_config.get("filter") or {}).get("transform", {}).get("type")
        if transform_type == "boolean":
            transformed_value = [transforms.coerce_boolean(value) for value in cleaned_values]
            transformed_value = [value for value in transformed_value if value is not None]
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
    excluded_names.add(field.field_name)

    operator_field_name = field.get_operator_field_name()
    if operator_field_name:
        excluded_names.add(operator_field_name)

    bool_not_field_name = field.get_bool_not_field_name()
    if bool_not_field_name:
        excluded_names.add(bool_not_field_name)

    return normalize_option_filters(
        applied_filters,
        excluded_filter_names=excluded_names,
    )


def normalize_option_filters(applied_filters, excluded_filter_names=None):
    excluded_filter_names = set(excluded_filter_names or [])
    normalized = {}

    for key, value in (applied_filters or {}).items():
        if str(key).startswith("__"):
            continue
        if key in excluded_filter_names:
            continue
        if key.endswith(FILTER_SUFFIXES):
            continue
        if value in (None, "", []):
            continue
        normalized[key] = value

    return normalized
