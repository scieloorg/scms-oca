from django.template.loader import render_to_string
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .normalization import group_options
from .normalization import normalize_options
from .normalization import normalize_selected_values
from .form_options import resolve_form_options
from .request_filters import CLEAR_DEFAULTS_INTERNAL_FLAG
from .service import SearchGatewayService
from .ui import build_form_groups


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


def _resolve_selected_values(applied_filters, field_name, default_value, clear_defaults):
    selected_values = normalize_selected_values(applied_filters, field_name)
    if selected_values or clear_defaults or default_value in (None, "", {}, []):
        return selected_values

    if isinstance(default_value, (list, tuple)):
        return [str(value) for value in default_value if value not in (None, "")]
    if isinstance(default_value, dict):
        return []
    return [str(default_value)]


def _resolve_range_value(applied_filters, source_name, default_value, clear_defaults):
    if not source_name:
        return ""
    current_value = (applied_filters or {}).get(source_name)
    if current_value not in (None, ""):
        return current_value
    if clear_defaults:
        return ""
    return default_value


def build_form_field_definition(field, applied_filters=None, options_by_field=None):
    ui_metadata = field.get_ui_metadata()
    widget = ui_metadata.get("widget") or field.get_widget_name()
    group_meta = dict(ui_metadata.get("group") or field.get_group_meta())
    group_label = group_meta.get("label")
    if isinstance(group_label, str) and group_label:
        group_meta["label"] = gettext(group_label)

    field_label = ui_metadata.get("label") or field.field_name
    if isinstance(field_label, str) and field_label:
        field_label = gettext(field_label)

    help_text = ui_metadata.get("help_text") or ""
    if isinstance(help_text, str) and help_text:
        help_text = gettext(help_text)

    configured_placeholder = ui_metadata.get("placeholder") or ""
    if isinstance(configured_placeholder, str) and configured_placeholder:
        configured_placeholder = gettext(configured_placeholder)

    default_value = ui_metadata.get("default_value", {})
    default_range_value = default_value if isinstance(default_value, dict) else {}
    multiple_selection = bool(ui_metadata.get("multiple_selection"))
    support_query_operator = bool(ui_metadata.get("support_query_operator"))
    searchable = bool(ui_metadata.get("searchable"))
    async_endpoint = str(ui_metadata.get("async_endpoint") or "")
    preload_options = bool(ui_metadata.get("preload_options"))
    dependencies = list(ui_metadata.get("dependencies") or [])
    range_sources = list(ui_metadata.get("transform_sources") or [])

    clear_defaults = bool((applied_filters or {}).get(CLEAR_DEFAULTS_INTERNAL_FLAG))
    default_search_placeholder = gettext("Search...")
    if default_search_placeholder == "Search...":
        default_search_placeholder = "Buscar..."

    selected_values = _resolve_selected_values(
        applied_filters,
        field.field_name,
        default_value,
        clear_defaults,
    )

    static_options = [
        {
            "value": option["value"],
            "label": option["label"],
            "group": option["group"],
        }
        for option in normalize_options(ui_metadata.get("static_options") or [], [])
    ]
    raw_runtime_options = (options_by_field or {}).get(field.field_name) or []
    raw_option_source = _merge_static_and_runtime_options(static_options, raw_runtime_options)
    options = normalize_options(raw_option_source, selected_values)
    options = _sort_options_for_display(field, widget, field_label, options)

    if widget in {"select", "lookup"} and (
        not configured_placeholder or configured_placeholder == field_label
    ):
        resolved_placeholder = default_search_placeholder
    else:
        resolved_placeholder = configured_placeholder

    range_start_name = range_sources[0] if len(range_sources) >= 1 else ""
    range_end_name = range_sources[1] if len(range_sources) >= 2 else ""
    range_start_value = _resolve_range_value(
        applied_filters,
        range_start_name,
        default_range_value.get("start", ""),
        clear_defaults,
    )
    range_end_value = _resolve_range_value(
        applied_filters,
        range_end_name,
        default_range_value.get("end", ""),
        clear_defaults,
    )

    is_active = _field_is_active(
        widget=widget,
        value=selected_values[0] if selected_values else "",
        range_start_value=range_start_value,
        range_end_value=range_end_value,
        options=options,
    )

    boolean_toggle_options = []
    if widget == "select" and not multiple_selection:
        boolean_toggle_options = _build_boolean_toggle_options(static_options or options, selected_values)

    bool_not_key = field.get_bool_not_field_name()
    operator_key = field.get_operator_field_name()
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
        "async_endpoint": async_endpoint,
        "preload_options": preload_options,
        "dependencies": dependencies,
        "placeholder": resolved_placeholder,
        "value": selected_values[0] if selected_values else "",
        "values": selected_values,
        "range_sources": range_sources,
        "range_start_name": range_start_name,
        "range_end_name": range_end_name,
        "range_start_value": range_start_value,
        "range_end_value": range_end_value,
        "range_values": {
            source_name: (applied_filters or {}).get(source_name, "")
            for source_name in range_sources
        },
        "options": options,
        "option_groups": group_options(options),
        "boolean_toggle_options": boolean_toggle_options,
        "boolean_toggle_clear_selected": not any(
            option.get("selected") for option in boolean_toggle_options
        ),
        "is_active": is_active,
        "has_visible_content": _field_has_visible_content(
            widget=widget,
            options=options,
            is_active=is_active,
            searchable=searchable,
            async_endpoint=async_endpoint,
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
        "input_type": ui_metadata.get("input_type", "text"),
        "min_value": ui_metadata.get("min_value"),
        "max_value": ui_metadata.get("max_value"),
        "step": ui_metadata.get("step"),
        "allow_clear": ui_metadata.get("allow_clear", True),
    }


def build_data_source_form_payload(
    data_source,
    *,
    form_key=None,
    applied_filters=None,
    include_fields=None,
    exclude_fields=None,
    excluded_filter_names=None,
):
    service = SearchGatewayService(index_name=data_source.index_name)
    form_fields = data_source.get_ordered_fields(
        form_key=form_key,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    options_by_field, errors = resolve_form_options(
        service,
        data_source,
        form_key=form_key,
        applied_filters=applied_filters,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
        excluded_filter_names=excluded_filter_names,
    )

    form_group_labels = data_source.get_form_group_labels(form_key) if form_key else {}
    field_definitions = [
        build_form_field_definition(
            field,
            applied_filters=applied_filters,
            options_by_field=options_by_field,
        )
        for field in form_fields
        if not field.is_hidden_in_form()
    ]
    form_groups = build_form_groups(field_definitions, form_group_labels=form_group_labels)

    metadata_fields = {field_definition["name"]: [] for field_definition in field_definitions}

    return {
        "form_groups": form_groups,
        "options_by_field": options_by_field,
        "errors": errors,
        "filter_metadata": data_source.get_filter_metadata(
            metadata_fields,
            form_key=form_key,
            include_fields=include_fields,
            exclude_fields=exclude_fields,
        ),
    }


def render_filter_sidebar(
    request,
    *,
    data_source,
    form_key,
    applied_filters=None,
    include_fields=None,
    exclude_fields=None,
    sidebar_form_id="search-gateway-filter-form",
    sidebar_form_method="get",
    sidebar_form_action="",
    submit_label=_("FILTRAR"),
    reset_label=_("LIMPAR"),
    submit_id="search-gateway-filter-submit",
    reset_id="search-gateway-filter-reset",
    reset_type="button",
    filters_error="",
):
    payload = build_data_source_form_payload(
        data_source,
        form_key=form_key,
        applied_filters=applied_filters,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    context = {
        "data_source": data_source.index_name,
        "form_key": form_key,
        "form_groups": payload["form_groups"],
        "sidebar_form_id": sidebar_form_id,
        "sidebar_form_method": sidebar_form_method,
        "sidebar_form_action": sidebar_form_action,
        "submit_label": submit_label,
        "reset_label": reset_label,
        "submit_id": submit_id,
        "reset_id": reset_id,
        "reset_type": reset_type,
        "filters_error": filters_error or " ".join(payload["errors"]).strip(),
    }
    html = render_to_string(
        "search_gateway/includes/filter_sidebar.html",
        context,
        request=request,
    )
    payload.update(
        {
            "form_html": html,
            "applied_filters": applied_filters or {},
        }
    )
    return payload
