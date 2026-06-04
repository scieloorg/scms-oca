from search_gateway.option_normalization import normalize_boolean


def clean_filters(filters_dict):
    cleaned = {k: v for k, v in filters_dict.items() if not _is_empty_filter_value(v)}
    cleaned.pop("csrfmiddlewaretoken", None)
    return cleaned


def normalize_filter_values(values: list, sort=True):
    vals = list(
        set(
            str(item).strip()
            for item in (values or [])
            if item is not None and str(item).strip() != ""
        )
    )

    if sort:
        return sorted(vals)

    return vals


def translate_filter_fields(filters, field_settings):
    translated = {}
    searchable = {}
    handled_by_transform = set()

    for fl_name, fl_settings in field_settings.items():
        transform_type = fl_settings.get("filter", {}).get("transform", {}).get("type")
        if not transform_type:
            continue

        index_field_name = fl_settings.get("index_field_name")
        if not index_field_name:
            continue

        value = None
        if transform_type == "boolean":
            value = normalize_boolean(filters.get(fl_name))
            handled_by_transform.add(fl_name)
        elif transform_type == "year_range":
            value = build_year_list_filter(filters, fl_settings)
            handled_by_transform.update(_transform_sources(fl_settings))
        elif transform_type == "date_year_range":
            value = build_date_range_filter(filters, fl_settings)
            handled_by_transform.update(_transform_sources(fl_settings))
        elif transform_type == "numeric_range":
            value = build_numeric_range_filter(filters, fl_settings)
            handled_by_transform.update(_transform_sources(fl_settings))

        if value is not None:
            translated[fl_name] = {
                "filter_name": fl_name,
                "value": value,
            }

    for fl_name, value in filters.items():
        if fl_name in handled_by_transform:
            continue

        fl_settings = field_settings.get(fl_name, {})
        index_field_name = fl_settings.get("index_field_name")

        if index_field_name and not _is_empty_filter_value(value):
            translated[fl_name] = {
                "filter_name": fl_name,
                "value": value,
            }

    for fl_name, data in translated.items():
        index_field_name = field_settings.get(fl_name, {}).get("index_field_name")
        searchable[index_field_name] = data.get("value")

    return searchable


def build_year_list_filter(filters, settings):
    source_field_names = _transform_sources(settings)
    if len(source_field_names) != 2:
        return None

    start_year_name, end_year_name = source_field_names
    return build_year_list(filters.get(start_year_name), filters.get(end_year_name))


def build_date_range_filter(filters, settings):
    source_field_names = _transform_sources(settings)
    if len(source_field_names) != 2:
        return None

    start_year_name, end_year_name = source_field_names
    start_year = _parse_year(filters.get(start_year_name))
    end_year = _parse_year(filters.get(end_year_name))

    if start_year is None and end_year is None:
        return None

    if start_year is not None and end_year is not None and start_year > end_year:
        start_year, end_year = end_year, start_year

    range_dict = {}
    if start_year is not None:
        range_dict["gte"] = f"{start_year}-01-01"
    if end_year is not None:
        range_dict["lte"] = f"{end_year}-12-31"

    return range_dict


def build_numeric_range_filter(filters, settings):
    source_field_names = _transform_sources(settings)
    if len(source_field_names) != 2:
        return None

    start_num_name, end_num_name = source_field_names
    start_num = _parse_int(filters.get(start_num_name))
    end_num = _parse_int(filters.get(end_num_name))

    if start_num is None and end_num is None:
        return None

    if start_num is not None and end_num is not None and start_num > end_num:
        start_num, end_num = end_num, start_num

    range_dict = {}
    if start_num is not None:
        range_dict["gte"] = start_num
    if end_num is not None:
        range_dict["lte"] = end_num

    return range_dict


def build_year_list(start_year, end_year):
    if not start_year and not end_year:
        return []

    start = _parse_int(start_year, fallback=1800)
    end = _parse_int(end_year, fallback=2100)

    if start > end:
        start, end = end, start

    return [str(y) for y in range(start, end + 1)]


def _is_empty_filter_value(value):
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    if isinstance(value, (list, tuple, set)):
        return all(_is_empty_filter_value(item) for item in value)

    return False


def _transform_sources(settings):
    return settings.get("filter", {}).get("transform", {}).get("sources", [])


def _parse_year(value):
    return _parse_int(value)


def _parse_int(value, fallback=None):
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback
