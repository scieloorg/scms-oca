from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from .request_filters import normalize_option_filters
from .service import SearchGatewayService
from .ui import build_data_source_form_groups


def _field_requires_runtime_options(field):
    return field.requires_runtime_options()


def _build_field_option_filters(
    applied_filters,
    field,
    *,
    excluded_filter_names=None,
):
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


def _append_selected_lookup_options(
    service,
    data_source,
    *,
    form_key=None,
    applied_filters=None,
    options_by_field=None,
    include_fields=None,
    exclude_fields=None,
):
    options_by_field = options_by_field if options_by_field is not None else {}
    applied_filters = applied_filters or {}

    for field in data_source.get_ordered_fields(
        form_key=form_key,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    ):
        lookup_config = field.get_lookup_config()
        if not lookup_config:
            continue

        selected_values = applied_filters.get(field.field_name)
        if selected_values in (None, "", []):
            continue
        if not isinstance(selected_values, (list, tuple)):
            selected_values = [selected_values]

        selected_values = [str(value).strip() for value in selected_values if str(value).strip()]
        if not selected_values:
            continue

        existing_options = options_by_field.get(field.field_name) or []
        known_values = {
            str(option.get("value") or option.get("key") or "").strip()
            for option in existing_options
            if isinstance(option, dict)
        }
        missing_values = [value for value in selected_values if value not in known_values]
        if not missing_values:
            continue

        lookup_options, _error = service.get_lookup_options_by_values(
            field.field_name,
            missing_values,
        )
        if not lookup_options:
            continue

        normalized_lookup_options = [
            {
                "value": str(option.get("key") or "").strip(),
                "label": str(option.get("label") or option.get("key") or "").strip(),
            }
            for option in lookup_options
            if str(option.get("key") or "").strip()
        ]
        if not normalized_lookup_options:
            continue

        options_by_field.setdefault(field.field_name, [])
        options_by_field[field.field_name].extend(normalized_lookup_options)


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
    option_filters = normalize_option_filters(
        applied_filters,
        excluded_filter_names=excluded_filter_names,
    )
    form_fields = data_source.get_ordered_fields(
        form_key=form_key,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    index_field_names = [field.field_name for field in form_fields if field.kind == "index"]

    filters_data, filters_error = service.get_filters_data(
        include_fields=index_field_names or include_fields,
        exclude_fields=exclude_fields,
        filters=option_filters,
    )
    options_by_field = dict(filters_data or {})
    field_errors = []

    for field in form_fields:
        if field.is_hidden_in_form():
            continue
        if field.field_name in options_by_field:
            continue
        if not _field_requires_runtime_options(field):
            continue

        field_option_filters = _build_field_option_filters(
            applied_filters,
            field,
            excluded_filter_names=excluded_filter_names,
        )
        options, error = service.get_field_options(
            field.field_name,
            query_text="",
            filters=field_option_filters,
        )
        if options is not None:
            options_by_field[field.field_name] = options
        if error:
            field_errors.append(error)

    _append_selected_lookup_options(
        service,
        data_source,
        form_key=form_key,
        applied_filters=applied_filters,
        options_by_field=options_by_field,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )

    form_groups = build_data_source_form_groups(
        data_source,
        form_key=form_key,
        applied_filters=applied_filters,
        options_by_field=options_by_field,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )

    errors = []
    if filters_error:
        errors.append(filters_error)
    errors.extend(field_errors)

    metadata_fields = {
        field.field_name: []
        for field in form_fields
        if not field.is_hidden_in_form()
    }

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
