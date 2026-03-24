from search_gateway.models import DataSource


JOURNAL_METRICS_DATA_SOURCE = "journal_metrics_by_*"


def _normalize_text(value, lower=False):
    normalized = str(value or "").strip()
    return normalized.lower() if lower else normalized


def get_journal_metrics_data_source():
    return DataSource.get_by_index_name(index_name=JOURNAL_METRICS_DATA_SOURCE)


def _get_resolved_field(field_name):
    data_source = get_journal_metrics_data_source()
    if not data_source:
        return None
    return data_source.get_field(field_name)


def _get_default_value(field_name, default=None):
    field = _get_resolved_field(field_name)
    if not field:
        return default

    value = field.default_value
    if value in (None, "", [], {}):
        return default
    return value


def _get_static_option_values(field_name, *, lower=False):
    field = _get_resolved_field(field_name)
    if not field:
        return tuple()

    values = []
    seen = set()
    for option in field.static_options:
        normalized_value = _normalize_text((option or {}).get("value"), lower=lower)
        if not normalized_value or normalized_value in seen:
            continue
        seen.add(normalized_value)
        values.append(normalized_value)
    return tuple(values)


def get_default_category_id():
    return _normalize_text(_get_default_value("category_id"))


def get_default_category_level():
    valid_levels = get_valid_category_levels()
    resolved_level = _normalize_text(_get_default_value("category_level"), lower=True)
    if resolved_level and resolved_level in valid_levels:
        return resolved_level
    return valid_levels[0] if valid_levels else ""


def get_default_publication_year():
    return _normalize_text(_get_default_value("publication_year"))


def get_default_minimum_publications():
    return normalize_minimum_publications(_get_default_value("minimum_publications")) or 1


def get_default_limit():
    resolved_limit = normalize_minimum_publications(_get_default_value("limit"))
    return resolved_limit or 100


def get_default_ranking_metric():
    allowed_metrics = get_allowed_ranking_metrics()
    resolved_metric = _normalize_text(_get_default_value("ranking_metric"))
    if resolved_metric and resolved_metric in allowed_metrics:
        return resolved_metric
    return allowed_metrics[0] if allowed_metrics else resolved_metric


def get_valid_category_levels():
    return _get_static_option_values("category_level", lower=True)


def get_category_level_order():
    return get_valid_category_levels()


def get_allowed_ranking_metrics():
    return _get_static_option_values("ranking_metric")


def normalize_ranking_metric(metric):
    metric_key = _normalize_text(metric)
    allowed_metrics = get_allowed_ranking_metrics()
    if metric_key and metric_key in allowed_metrics:
        return metric_key
    return get_default_ranking_metric() or metric_key


def get_index_field_name(field_name):
    resolved_name = _normalize_text(field_name)
    data_source = get_journal_metrics_data_source()
    if not data_source:
        return resolved_name
    return _normalize_text(data_source.get_index_field_name(field_name) or resolved_name)


def normalize_category_level(category_level):
    value = _normalize_text(category_level, lower=True)
    valid_levels = get_valid_category_levels()
    if value and value in valid_levels:
        return value
    return get_default_category_level() or value


def normalize_minimum_publications(value):
    if value in (None, ""):
        return None

    try:
        normalized_value = int(value)
    except (TypeError, ValueError):
        return None

    return normalized_value if normalized_value >= 1 else None
