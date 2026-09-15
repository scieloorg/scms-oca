def clean_filters(filters_dict):
    cleaned = {k: v for k, v in filters_dict.items() if not _is_empty_filter_value(v)}
    cleaned.pop("csrfmiddlewaretoken", None)
    return cleaned


def _is_empty_filter_value(value):
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    if isinstance(value, (list, tuple, set)):
        return all(_is_empty_filter_value(item) for item in value)

    return False
