from .utils.normalization import normalize_selected_values
from .request_filters import build_option_filters
from .request_filters import normalize_option_filters


def _normalize_lookup_option(option):
    return {
        "value": str(option["key"]),
        "label": str(option.get("label") or option["key"]),
    }


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
        if not field.lookup:
            continue

        selected_values = normalize_selected_values(applied_filters, field.field_name)
        if not selected_values:
            continue

        existing_options = options_by_field.get(field.field_name) or []
        known_values = {
            str(option.get("value") or option.get("key") or "")
            for option in existing_options
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

        options_by_field.setdefault(field.field_name, [])
        options_by_field[field.field_name].extend(
            _normalize_lookup_option(option) for option in lookup_options
        )


def resolve_form_options(
    service,
    data_source,
    *,
    form_key=None,
    applied_filters=None,
    include_fields=None,
    exclude_fields=None,
    excluded_filter_names=None,
):
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
        if field.hidden_in_form:
            continue
        if field.field_name in options_by_field:
            continue
        if not field.requires_runtime_options:
            continue

        field_option_filters = build_option_filters(
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

    errors = []
    if filters_error:
        errors.append(filters_error)
    errors.extend(field_errors)
    return options_by_field, errors