from collections import OrderedDict

from django.utils.translation import gettext


TRUE_VALUES = {"true", "1", "yes", "y", "sim", "on"}
FALSE_VALUES = {"false", "0", "no", "n", "nao"}

SEARCH_RESULT_SORT_VALUES = frozenset({"desc", "asc", "cited_by_count"})


def normalize_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_positive_number(value, default: int) -> int:
    normalized = normalize_int(value, default)
    return normalized if normalized > 0 else default


def normalize_search_result_sort(value):
    normalized = str(value or "desc").strip().lower()
    return normalized if normalized in SEARCH_RESULT_SORT_VALUES else "desc"


def normalize_filter_default_value(default_value):
    if isinstance(default_value, (list, tuple)):
        values = [str(item) for item in default_value if item not in (None, "")]
        if not values:
            return None
        return values if len(values) > 1 else values[0]
    return str(default_value)


def normalize_selected_values(applied_filters, field_name, default=None):
    applied_filters = applied_filters or {}
    value = applied_filters.get(field_name, default)

    if value in (None, ""):
        return []

    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item not in (None, "")]

    return [str(value)]


def normalize_option(option, selected_values):
    if isinstance(option, dict):
        value = option.get("value", option.get("key", option.get("id")))
        label = option.get("label", option.get("text", value))
        group = option.get("group")
    else:
        value = option
        label = option
        group = None

    normalized_value = "" if value is None else str(value)
    normalized_label = gettext(label) if isinstance(label, str) and label else label
    normalized_group = gettext(group) if isinstance(group, str) and group else group

    return {
        "value": normalized_value,
        "label": normalized_label or normalized_value,
        "group": normalized_group,
        "selected": normalized_value in selected_values,
    }


def normalize_options(options, selected_values):
    normalized = [
        normalize_option(option, selected_values)
        for option in (options or [])
        if option not in (None, "")
    ]

    known_values = {option["value"] for option in normalized}
    for selected_value in selected_values:
        if selected_value in known_values:
            continue
        normalized.append(
            {
                "value": selected_value,
                "label": selected_value,
                "group": None,
                "selected": True,
            }
        )
    return normalized


def group_options(options):
    ungrouped = []
    groups = OrderedDict()

    for option in options:
        group_label = option.get("group")
        if not group_label:
            ungrouped.append(option)
            continue
        groups.setdefault(group_label, []).append(option)

    option_groups = []
    if ungrouped:
        option_groups.append({"label": "", "options": ungrouped})
    option_groups.extend(
        {"label": label, "options": grouped_options}
        for label, grouped_options in groups.items()
    )
    return option_groups


def normalize_boolean(value):
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
        return None

    if value in (True, 1):
        return True
    if value in (False, 0):
        return False
    return None
