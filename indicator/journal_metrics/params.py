import re

from django.http import QueryDict
from django.urls import reverse

from .config import (
    DEFAULT_CATEGORY_ID,
    DEFAULT_MINIMUM_PUBLICATIONS,
    normalize_category_level,
    normalize_minimum_publications,
    normalize_ranking_metric,
)
from ..search import utils as search_utils

ISSN_PATTERN = re.compile(r"^\d{4}-[\dXx]{4}$")

PROFILE_ROUTE_PARAM_KEYS = {"issn", "journal", "journal_issn", "journal_title"}
PROFILE_QUERY_PARAM_KEYS = ("collection", "publication_year", "category_level", "category_id")
PROFILE_PASSTHROUGH_PARAM_KEYS = {"collection"}
PROFILE_NON_FILTER_KEYS = PROFILE_ROUTE_PARAM_KEYS | {
    "category_id",
    "category_level",
    "publication_year",
    "year",
    "ranking_metric",
    "limit",
    "minimum_publications",
    "scope",
    "return_study_unit",
    "study_unit",
}
RANKING_CONFIGURATION_KEYS = {
    "publication_year",
    "ranking_metric",
    "limit",
    "category_level",
    "category_id",
    "minimum_publications",
}
TIMESERIES_NON_FILTER_KEYS = PROFILE_NON_FILTER_KEYS | {"minimum_publications"}


def looks_like_issn(value):
    return bool(ISSN_PATTERN.fullmatch(str(value or "").strip()))


def get_profile_issn(params, issn=None):
    if issn:
        return str(issn).strip()

    journal_param = str(params.get("journal") or params.get("issn") or "").strip()
    return journal_param if looks_like_issn(journal_param) else ""


def build_profile_url(params, issn):
    redirect_url = reverse("indicator_journal_metrics")
    source_params = params.copy()

    for key in PROFILE_ROUTE_PARAM_KEYS:
        if key in source_params:
            source_params.pop(key)

    query_params = QueryDict("", mutable=True)
    query_params["journal"] = str(issn).strip()

    source_items = list(source_params.lists()) if hasattr(source_params, "lists") else list(dict(source_params).items())

    for key in PROFILE_QUERY_PARAM_KEYS:
        for source_key, source_values in source_items:
            if source_key != key:
                continue

            values = source_values if isinstance(source_values, (list, tuple)) else [source_values]
            for value in values:
                query_params.appendlist(key, value)
            break

    query_string = query_params.urlencode()
    return f"{redirect_url}?{query_string}" if query_string else redirect_url


def normalize_request_filters(filters, source_filters=None, clean=False):
    normalized_filters = search_utils.clean_form_filters(dict(filters or {})) if clean else dict(filters or {})
    source_filters = source_filters if source_filters is not None else filters or {}

    for key in ("scope", "return_study_unit", "study_unit"):
        normalized_filters.pop(key, None)

    if "year" in normalized_filters and "publication_year" not in normalized_filters:
        normalized_filters["publication_year"] = normalized_filters.pop("year")

    if "ranking_metric" in normalized_filters:
        normalized_filters["ranking_metric"] = normalize_ranking_metric(normalized_filters.get("ranking_metric"))

    normalized_filters["category_level"] = normalize_category_level(normalized_filters.get("category_level"))

    has_explicit_category_level = str(source_filters.get("category_level") or "").strip() != ""
    has_explicit_category_id = str(source_filters.get("category_id") or "").strip() != ""
    if not has_explicit_category_level and not has_explicit_category_id:
        normalized_filters["category_id"] = DEFAULT_CATEGORY_ID

    minimum_publications = normalize_minimum_publications(source_filters.get("minimum_publications"))
    normalized_filters["minimum_publications"] = str(minimum_publications or DEFAULT_MINIMUM_PUBLICATIONS)

    return normalized_filters


def extract_profile_passthrough_filters(filters):
    return {
        key: str(filters.get(key) or "").strip()
        for key in PROFILE_PASSTHROUGH_PARAM_KEYS
        if str(filters.get(key) or "").strip()
    }


def build_timeseries_request(params):
    issn = str(params.get("issn") or params.get("journal_issn") or "").strip()
    journal_param = str(params.get("journal") or "").strip()
    if not issn and looks_like_issn(journal_param):
        issn = journal_param

    form_filters = dict(params or {})
    for key in TIMESERIES_NON_FILTER_KEYS:
        form_filters.pop(key, None)

    return {
        "issn": issn or None,
        "category_id": params.get("category_id"),
        "category_level": params.get("category_level"),
        "publication_year": params.get("publication_year"),
        "form_filters": search_utils.clean_form_filters(form_filters),
    }
