from indicator_journal.search.values import (
    GLOBAL_METRICS_BOOL_FIELDS,
    GLOBAL_METRICS_TEXT_FIELDS,
    DEFAULT_GLOBAL_METRIC,
    DEFAULT_GLOBAL_YEAR,
    DEFAULT_GLOBAL_LIMIT,
)
from indicator_journal.search.utils import safe_int


def normalize_global_request_filters(request_filters):
    """Normalize parameters for the global ranking query."""
    year = request_filters.get("publication_year") or DEFAULT_GLOBAL_YEAR
    metric = request_filters.get("ranking_metric") or DEFAULT_GLOBAL_METRIC
    limit = safe_int(request_filters.get("limit")) or DEFAULT_GLOBAL_LIMIT

    # Base configuration
    clean_params = {
        "publication_year": year,
        "ranking_metric": metric,
        "limit": limit,
    }

    # Extract dynamic filters
    filters = {}
    for form_key in list(GLOBAL_METRICS_TEXT_FIELDS) + list(GLOBAL_METRICS_BOOL_FIELDS):
        val = request_filters.get(form_key)
        if val:
            filters[form_key] = val

    clean_params["filters"] = filters
    return clean_params
