from collections import OrderedDict

from django.utils.translation import gettext


def normalize_widget_name(widget_name, transform_type=None, has_lookup=False):
    normalized_widget = str(widget_name or "").strip().lower()
    if normalized_widget in {"lookup", "select", "range", "text", "number", "year"}:
        return normalized_widget
    if transform_type == "year_range":
        return "range"
    if has_lookup or normalized_widget in {"autocomplete"}:
        return "lookup"
    if normalized_widget in {"input", "string"}:
        return "text"
    return "select"


def normalize_group_key(group_key, default="default"):
    normalized = str(group_key or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or default


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
