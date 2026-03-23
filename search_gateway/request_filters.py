from django.conf import settings


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


def extract_applied_filters(source, data_source, form_key=None, extra_excluded_keys=None):
    extra_excluded_keys = set(extra_excluded_keys or [])
    excluded_keys = set(EXCLUDED_QUERY_KEYS) | extra_excluded_keys
    field_names = set()
    transform_source_names = set()

    for field in data_source.get_ordered_fields(form_key=form_key):
        field_names.add(field.field_name)
        transform_source_names.update(field.get_transform_sources())
        if field.supports_query_operator():
            field_names.add(field.get_operator_field_name())
            field_names.add(field.get_bool_not_field_name())

    allowed_keys = field_names | transform_source_names
    applied_filters = {}

    for key in source.keys():
        if key in excluded_keys:
            continue
        if allowed_keys and key not in allowed_keys:
            continue

        values = [value for value in source.getlist(key) if value not in (None, "")]
        if not values:
            continue
        applied_filters[key] = values if len(values) > 1 else values[0]

    if _should_skip_default_filters(source):
        applied_filters[CLEAR_DEFAULTS_INTERNAL_FLAG] = True
        return applied_filters

    return _apply_default_filters(applied_filters, data_source, form_key=form_key)


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
