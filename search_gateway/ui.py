from collections import OrderedDict

from django.utils.text import capfirst
from django.utils.translation import gettext

from .normalization import group_options
from .normalization import normalize_group_key
from .normalization import normalize_options
from .normalization import normalize_selected_values
from .request_filters import CLEAR_DEFAULTS_INTERNAL_FLAG


def _field_is_active(*, widget, value="", range_start_value="", range_end_value="", options=None):
    if widget == "range":
        return range_start_value not in (None, "") or range_end_value not in (None, "")
    if widget in {"text", "number", "year"}:
        return value not in (None, "")
    return any(option.get("selected") for option in (options or []))


def _field_has_visible_content(*, widget, options=None, is_active=False, searchable=False, async_endpoint=""):
    if widget in {"range", "text", "number", "year"}:
        return True
    if is_active:
        return True
    if widget == "lookup":
        return bool(async_endpoint or searchable or options)
    return bool(options)


def _build_group_meta(group_key, explicit_label=None, explicit_order=None):
    normalized_key = normalize_group_key(group_key, default="default")
    label = explicit_label or capfirst(str(normalized_key).replace("_", " "))
    order = explicit_order if explicit_order is not None else 999
    return {"key": normalized_key, "label": label, "order": order}


def _resolve_filter_ui_context(field):
    ui_metadata = field.get_ui_metadata()

    widget = ui_metadata.get("widget") or field.get_widget_name()

    static_options_source = ui_metadata.get("static_options")
    if static_options_source in (None, ""):
        static_options_source = field.get_static_options()
    options = normalize_options(static_options_source, [])
    static_options = [
        {"value": option["value"], "label": option["label"], "group": option["group"]}
        for option in options
    ]

    group_meta = dict(ui_metadata.get("group") or {})
    if not group_meta:
        group_meta = field.get_group_meta()
    group_label = group_meta.get("label")
    group_meta["label"] = (
        gettext(group_label) if isinstance(group_label, str) and group_label else None
    ) or capfirst(str(group_meta.get("key") or "default").replace("_", " "))

    async_endpoint = ui_metadata.get("async_endpoint")
    if async_endpoint in (None, ""):
        async_endpoint = field.get_async_endpoint()

    searchable = ui_metadata.get("searchable")
    if searchable is None:
        searchable = field.is_searchable()
    searchable = bool(searchable)

    range_sources = list(ui_metadata.get("transform_sources") or [])
    if not range_sources:
        range_sources = field.get_transform_sources()

    return {
        "ui_metadata": ui_metadata,
        "widget": widget,
        "group_meta": group_meta,
        "async_endpoint": async_endpoint or "",
        "searchable": searchable,
        "range_sources": range_sources,
        "static_options": static_options,
    }


def _build_boolean_toggle_options(options, selected_values):
    normalized_selected_values = {
        str(value or "").strip().lower()
        for value in (selected_values or [])
        if str(value or "").strip()
    }
    normalized_options = []
    option_labels = {}

    for option in options or []:
        option_value = str(option.get("value") or "").strip().lower()
        if option_value not in {"true", "false"}:
            continue
        if option_value not in option_labels:
            option_labels[option_value] = option.get("label") or option_value

    if set(option_labels.keys()) != {"true", "false"}:
        return []

    for option_value in ("true", "false"):
        normalized_options.append(
            {
                "value": option_value,
                "label": option_labels[option_value],
                "selected": option_value in normalized_selected_values,
            }
        )

    return normalized_options


def _parse_year_option_value(option):
    raw_value = str((option or {}).get("value") or "").strip()
    if not raw_value or not raw_value.lstrip("-").isdigit():
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _field_prefers_descending_year_options(field, widget, field_label):
    normalized_name = str(getattr(field, "field_name", "") or "").strip().lower()
    normalized_label = str(field_label or "").strip().lower()

    if widget == "year":
        return True
    if normalized_name.endswith("_year"):
        return True
    return "year" in normalized_label


def _sort_options_for_display(field, widget, field_label, options):
    if not _field_prefers_descending_year_options(field, widget, field_label):
        return options

    sortable = []
    unsortable = []

    for index, option in enumerate(options or []):
        parsed_year = _parse_year_option_value(option)
        if parsed_year is None:
            unsortable.append((index, option))
            continue
        sortable.append((parsed_year, index, option))

    if not sortable:
        return options

    sorted_options = [
        option
        for _year, _index, option in sorted(sortable, key=lambda item: (-item[0], item[1]))
    ]
    sorted_options.extend(option for _index, option in unsortable)
    return sorted_options


def _merge_static_and_runtime_options(static_options, runtime_options):
    merged = []
    seen_values = set()

    for option in (static_options or []):
        value = str((option or {}).get("value") or "")
        if value in seen_values:
            continue
        merged.append(option)
        seen_values.add(value)

    for option in (runtime_options or []):
        value = str((option or {}).get("value") or (option or {}).get("key") or "")
        if value in seen_values:
            continue
        merged.append(option)
        seen_values.add(value)

    return merged


def build_form_field_definition(field, applied_filters=None, options_by_field=None):
    context = _resolve_filter_ui_context(field)
    ui_metadata = context["ui_metadata"]
    widget = context["widget"]
    group_meta = context["group_meta"]
    async_endpoint = context["async_endpoint"]
    searchable = context["searchable"]
    range_sources = context["range_sources"]

    configured_label = ui_metadata.get("label")
    if configured_label in (None, ""):
        configured_label = field.get_label(default=None)
    field_label = (
        gettext(configured_label) if isinstance(configured_label, str) and configured_label else configured_label
    ) or field.field_name

    configured_placeholder = ui_metadata.get("placeholder")
    if configured_placeholder in (None, ""):
        configured_placeholder = field.get_placeholder(default="")
    if isinstance(configured_placeholder, str) and configured_placeholder:
        configured_placeholder = gettext(configured_placeholder)

    help_text = ui_metadata.get("help_text")
    if help_text in (None, ""):
        help_text = field.get_help_text(default="")
    if isinstance(help_text, str) and help_text:
        help_text = gettext(help_text)

    default_value = ui_metadata.get("default_value")
    if default_value in (None, ""):
        default_value = field.get_default_value(default={})
    default_range_value = default_value if isinstance(default_value, dict) else {}

    multiple_selection = ui_metadata.get("multiple_selection")
    if multiple_selection is None:
        multiple_selection = field.allows_multiple_selection()

    support_query_operator = ui_metadata.get("support_query_operator")
    if support_query_operator is None:
        support_query_operator = field.supports_query_operator()
    support_query_operator = bool(support_query_operator)

    preload_options = ui_metadata.get("preload_options")
    if preload_options is None:
        preload_options = field.is_preload_options()
    preload_options = bool(preload_options)

    dependencies = list(ui_metadata.get("dependencies") or [])
    if not dependencies:
        dependencies = field.get_dependencies()

    clear_defaults = bool((applied_filters or {}).get(CLEAR_DEFAULTS_INTERNAL_FLAG))
    default_search_placeholder = gettext("Search...")
    if default_search_placeholder == "Search...":
        default_search_placeholder = "Buscar..."

    selected_values = normalize_selected_values(applied_filters, field.field_name)
    if not selected_values and not clear_defaults and default_value not in (None, "", {}, []):
        if isinstance(default_value, (list, tuple)):
            selected_values = [str(value) for value in default_value if value not in (None, "")]
        elif not isinstance(default_value, dict):
            selected_values = [str(default_value)]

    raw_runtime_options = (options_by_field or {}).get(field.field_name) or []
    raw_option_source = (
        _merge_static_and_runtime_options(context["static_options"], raw_runtime_options)
        if context["static_options"]
        else raw_runtime_options
    )
    options = normalize_options(
        raw_option_source,
        selected_values,
    )
    options = _sort_options_for_display(field, widget, field_label, options)
    boolean_toggle_options = []

    if widget in {"select", "lookup"}:
        if not configured_placeholder or configured_placeholder == field_label:
            resolved_placeholder = default_search_placeholder
        else:
            resolved_placeholder = configured_placeholder
    else:
        resolved_placeholder = configured_placeholder

    range_start_value = (
        (applied_filters or {}).get(range_sources[0])
        if len(range_sources) >= 1 and (applied_filters or {}).get(range_sources[0]) not in (None, "")
        else ("" if clear_defaults else default_range_value.get("start", ""))
        if len(range_sources) >= 1 else ""
    )
    range_end_value = (
        (applied_filters or {}).get(range_sources[1])
        if len(range_sources) >= 2 and (applied_filters or {}).get(range_sources[1]) not in (None, "")
        else ("" if clear_defaults else default_range_value.get("end", ""))
        if len(range_sources) >= 2 else ""
    )
    bool_not_key = field.get_bool_not_field_name()
    operator_key = field.get_operator_field_name()

    is_active = _field_is_active(
        widget=widget,
        value=selected_values[0] if selected_values else "",
        range_start_value=range_start_value,
        range_end_value=range_end_value,
        options=options,
    )

    if widget == "select" and not multiple_selection:
        boolean_toggle_options = _build_boolean_toggle_options(
            context["static_options"] or options,
            selected_values,
        )

    return {
        "name": field.field_name,
        "kind": field.kind,
        "label": field_label,
        "help_text": help_text,
        "widget": widget,
        "group": group_meta,
        "multiple_selection": multiple_selection,
        "support_query_operator": support_query_operator,
        "searchable": searchable,
        "async_endpoint": async_endpoint or "",
        "preload_options": preload_options,
        "dependencies": dependencies,
        "placeholder": resolved_placeholder,
        "value": selected_values[0] if selected_values else "",
        "values": selected_values,
        "range_sources": range_sources,
        "range_start_name": range_sources[0] if len(range_sources) >= 1 else "",
        "range_end_name": range_sources[1] if len(range_sources) >= 2 else "",
        "range_start_value": range_start_value,
        "range_end_value": range_end_value,
        "range_values": {
            source_name: (applied_filters or {}).get(source_name, "")
            for source_name in range_sources
        },
        "options": options,
        "option_groups": group_options(options),
        "boolean_toggle_options": boolean_toggle_options,
        "boolean_toggle_clear_selected": not any(option.get("selected") for option in boolean_toggle_options),
        "is_active": is_active,
        "has_visible_content": _field_has_visible_content(
            widget=widget,
            options=options,
            is_active=is_active,
            searchable=searchable,
            async_endpoint=async_endpoint or "",
        ),
        "operator_mode": (
            "and_or"
            if support_query_operator and multiple_selection
            else "not"
            if support_query_operator
            else ""
        ),
        "bool_not_active": str((applied_filters or {}).get(bool_not_key) or "").lower() == "true",
        "query_operator_value": str((applied_filters or {}).get(operator_key) or "and").lower(),
        "input_type": ui_metadata.get("input_type", field.get_ui_setting("input_type", "text")),
        "min_value": ui_metadata.get("min_value", field.get_ui_setting("min")),
        "max_value": ui_metadata.get("max_value", field.get_ui_setting("max")),
        "step": ui_metadata.get("step", field.get_ui_setting("step")),
        "allow_clear": ui_metadata.get("allow_clear", field.get_ui_setting("allow_clear", True)),
    }


def build_data_source_form_groups(
    data_source,
    *,
    form_key=None,
    applied_filters=None,
    options_by_field=None,
    include_fields=None,
    exclude_fields=None,
):
    fields = []
    form_group_labels = data_source.get_form_group_labels(form_key) if form_key else {}

    for field in data_source.get_ordered_fields(
        form_key=form_key,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    ):
        if field.is_hidden_in_form():
            continue
        fields.append(
            build_form_field_definition(
                field,
                applied_filters=applied_filters,
                options_by_field=options_by_field,
            )
        )

    fields = [field for field in fields if field.get("has_visible_content")]

    grouped_fields = OrderedDict()
    for field in fields:
        group_key = field["group"]["key"]
        group_label = form_group_labels.get(group_key, field["group"]["label"])
        if group_key not in grouped_fields:
            grouped_fields[group_key] = {
                "key": group_key,
                "label": group_label,
                "order": field["group"]["order"],
                "fields": [],
            }
        grouped_fields[group_key]["fields"].append(field)

    grouped_items = sorted(grouped_fields.values(), key=lambda item: (item["order"], item["label"]))
    has_active_fields = any(
        field.get("is_active")
        for group in grouped_items
        for field in group.get("fields", [])
    )

    for group in grouped_items:
        group_is_active = any(field.get("is_active") for field in group.get("fields", []))
        group["expanded"] = group_is_active if has_active_fields else True
        for field in group.get("fields", []):
            field["expanded"] = field.get("is_active") if has_active_fields else True

    return grouped_items
