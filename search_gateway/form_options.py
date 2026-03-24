from .request_filters import build_option_filters
from .request_filters import normalize_option_filters


def _field_requires_runtime_options(field):
    return field.requires_runtime_options()


def _append_selected_lookup_options(
    service,
    form_fields,
    *,
    applied_filters=None,
    options_by_field=None,
):
    options_by_field = options_by_field if options_by_field is not None else {}
    applied_filters = applied_filters or {}

    for field in form_fields:
        if not field.get_lookup_config():
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


def resolve_form_options(
    service,
    form_fields,
    *,
    applied_filters=None,
    include_fields=None,
    exclude_fields=None,
    excluded_filter_names=None,
):
    option_filters = normalize_option_filters(
        applied_filters,
        excluded_filter_names=excluded_filter_names,
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
        form_fields,
        applied_filters=applied_filters,
        options_by_field=options_by_field,
    )

    errors = []
    if filters_error:
        errors.append(filters_error)
    errors.extend(field_errors)
    return options_by_field, errors
