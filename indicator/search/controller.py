from search_gateway.client import get_opensearch_client
from search_gateway import data_sources_with_settings

from . import query as indicator_query
from . import parser as indicator_parser
from . import utils


BASELINE_PRESERVED_FILTER_KEYS = {
    "scope",
    "publication_year",
    "document_publication_year_start",
    "document_publication_year_end",
    "document_publication_year_range",
}

CONTROL_FILTER_KEYS = {
    "breakdown_variable",
    "study_unit",
    "return_study_unit",
    "csrfmiddlewaretoken",
}

DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL = "field"
VALID_JOURNAL_METRICS_CATEGORY_LEVELS = {"domain", "field", "subfield", "topic"}
DEFAULT_JOURNAL_METRICS_PUBLICATION_YEAR = "2020"
DEFAULT_JOURNAL_METRICS_RANKING_METRIC = "journal_impact_normalized_window_3y"


def _normalize_indicator_study_unit(study_unit):
    value = str(study_unit or "").strip().lower()
    if value in ("source", "journal"):
        return "journal"
    return "document"


def _has_filter_value(value):
    if isinstance(value, list):
        return any(str(item).strip() for item in value if item is not None)
    return str(value).strip() != ""


def _build_comparison_baseline_filters(filters):
    if not isinstance(filters, dict):
        return {}, []

    baseline_filters = {}
    comparative_filter_keys = []

    for key, value in filters.items():
        if key in CONTROL_FILTER_KEYS:
            continue
        if key.endswith("_operator") or key.endswith("_bool_not"):
            continue
        if not _has_filter_value(value):
            continue

        if key in BASELINE_PRESERVED_FILTER_KEYS:
            baseline_filters[key] = value
            operator_key = f"{key}_operator"
            bool_not_key = f"{key}_bool_not"
            if _has_filter_value(filters.get(operator_key)):
                baseline_filters[operator_key] = filters.get(operator_key)
            if _has_filter_value(filters.get(bool_not_key)):
                baseline_filters[bool_not_key] = filters.get(bool_not_key)
            continue

        comparative_filter_keys.append(key)

    return baseline_filters, comparative_filter_keys


def _normalize_journal_metrics_category_level(category_level):
    value = str(category_level or "").strip().lower()
    if not value:
        return DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL
    if value not in VALID_JOURNAL_METRICS_CATEGORY_LEVELS:
        return DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL
    return value


def _build_journal_metrics_filter_clauses(form_filters, selected_category_level):
    data_source = "journal_metrics"
    field_settings = data_sources_with_settings.get_field_settings(data_source)

    cleaned_filters = utils.clean_form_filters(dict(form_filters or {}))
    for key in (
        "publication_year",
        "year",
        "ranking_metric",
        "limit",
        "scope",
        "return_study_unit",
        "study_unit",
        "csrfmiddlewaretoken",
        "journal_title",
        "journal_issn",
        "category_id",
        "category_level",
    ):
        cleaned_filters.pop(key, None)

    cleaned_filters["category_level"] = selected_category_level

    query = indicator_query.build_query(cleaned_filters, field_settings, data_source)
    if isinstance(query, dict) and "bool" in query:
        bool_query = query.get("bool") or {}
        return list(bool_query.get("must", [])), list(bool_query.get("must_not", []))

    return [], []


def get_journal_metrics_data(form_filters):
    """
    Orchestrates the retrieval of journal metrics data.
    """
    es = get_opensearch_client()

    data_source = "journal_metrics"
    data_source_config = data_sources_with_settings.get_data_source(data_source)
    index_name = data_source_config.get("index_name") if data_source_config else None
    field_settings = data_source_config.get("field_settings", {}) if data_source_config else {}
    if not index_name:
        return None, "Invalid data_source"

    payload_filters = dict(form_filters)
    payload_filters["category_level"] = _normalize_journal_metrics_category_level(
        payload_filters.get("category_level")
    )

    publication_year = payload_filters.pop("publication_year", None) or payload_filters.pop("year", None)
    ranking_metric = payload_filters.pop("ranking_metric", DEFAULT_JOURNAL_METRICS_RANKING_METRIC)
    limit = payload_filters.pop("limit", 100)

    allowed_ranking_metrics = {
        "journal_publications_count",
        "journal_citations_total",
        "journal_citations_mean",
        "journal_citations_mean_window_2y",
        "journal_citations_mean_window_3y",
        "journal_citations_mean_window_5y",
        "journal_impact_normalized",
        "journal_impact_normalized_window_2y",
        "journal_impact_normalized_window_3y",
        "journal_impact_normalized_window_5y",
        "top_1pct_all_time_publications_share_pct",
        "top_5pct_all_time_publications_share_pct",
        "top_10pct_all_time_publications_share_pct",
        "top_50pct_all_time_publications_share_pct",
    }
    if ranking_metric not in allowed_ranking_metrics:
        ranking_metric = DEFAULT_JOURNAL_METRICS_RANKING_METRIC

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 5000))

    if not publication_year:
        publication_year = DEFAULT_JOURNAL_METRICS_PUBLICATION_YEAR

    cleaned_filters = utils.clean_form_filters(payload_filters)

    query = indicator_query.build_query(cleaned_filters, field_settings, data_source)
    jm_query = indicator_query.build_journal_metrics_query(publication_year, query)

    body = indicator_query.build_journal_metrics_body(
        selected_year=publication_year,
        ranking_metric=ranking_metric,
        query=jm_query,
        size=limit,
    )

    try:
        res = es.search(index=index_name, body=body)
        ranking_data = indicator_parser.parse_journal_metrics_response(
            res, selected_year=publication_year, ranking_metric=ranking_metric
        )
        return ranking_data, None
    except Exception as e:
        return None, f"Error executing search: {e}"


def get_journal_metrics_timeseries(
    issn=None,
    journal=None,
    category_id=None,
    category_level=None,
    publication_year=None,
    form_filters=None,
):
    """Fetch per-year series for a single journal from the journal_metrics index."""
    if not issn and not journal:
        return None, "Missing journal identifier"

    es = get_opensearch_client()

    data_source = "journal_metrics"
    data_source_config = data_sources_with_settings.get_data_source(data_source)
    index_name = data_source_config.get("index_name") if data_source_config else None
    if not index_name:
        return None, "Invalid data_source"

    selected_category_level = _normalize_journal_metrics_category_level(category_level)
    inherited_must, inherited_must_not = _build_journal_metrics_filter_clauses(
        form_filters,
        selected_category_level,
    )

    base_must = list(inherited_must)
    if issn:
        base_must.append({"term": {"journal_issn": issn}})
    if journal:
        base_must.append({"term": {"journal_title": journal}})

    categories_must = list(base_must)
    categories_must.append({"term": {"category_level": selected_category_level}})

    if publication_year not in (None, ""):
        try:
            categories_year = int(publication_year)
        except (TypeError, ValueError):
            categories_year = publication_year
        categories_must.append({"term": {"publication_year": categories_year}})

    categories_body = {
        "size": 0,
        "query": {
            "bool": {
                "must": categories_must,
                **({"must_not": inherited_must_not} if inherited_must_not else {}),
            }
        },
        "aggs": {
            "categories": {
                "terms": {
                    "field": "category_id",
                    "size": 2000,
                    "order": {"publications_total": "desc"},
                },
                "aggs": {
                    "publications_total": {"sum": {"field": "journal_publications_count"}},
                },
            }
        },
    }

    selected_category_id = str(category_id).strip() if category_id not in (None, "") else None
    available_categories = []
    try:
        categories_res = es.search(index=index_name, body=categories_body)
        available_categories = indicator_parser.parse_terms_agg_keys(categories_res, "categories")
        if selected_category_id and selected_category_id not in available_categories:
            selected_category_id = None
        if not selected_category_id and available_categories:
            selected_category_id = available_categories[0]
    except Exception:
        available_categories = []

    data_must = list(base_must)
    data_must.append({"term": {"category_level": selected_category_level}})
    if selected_category_id:
        data_must.append({"term": {"category_id": selected_category_id}})

    body = {
        "size": 1000,
        "query": {
            "bool": {
                "must": data_must,
                **({"must_not": inherited_must_not} if inherited_must_not else {}),
            }
        },
        "sort": [
            {"publication_year": {"order": "asc"}},
            {"journal_impact_normalized": {"order": "desc", "missing": "_last"}},
        ],
        "collapse": {"field": "publication_year"},
        "_source": indicator_query.JOURNAL_METRICS_SOURCE_FIELDS,
    }

    try:
        res = es.search(index=index_name, body=body)
    except Exception as e:
        return None, f"Error executing search: {e}"

    hits = res.get("hits", {}).get("hits", [])
    if not hits:
        return None, "Not found"

    parsed = indicator_parser.parse_journal_metrics_timeseries(hits)
    spider_must = list(base_must)
    spider_must.append({"term": {"category_level": selected_category_level}})
    if publication_year not in (None, ""):
        try:
            spider_year = int(publication_year)
        except (TypeError, ValueError):
            spider_year = publication_year
        spider_must.append({"term": {"publication_year": spider_year}})

    category_spider_body = {
        "size": 0,
        "query": {
            "bool": {
                "must": spider_must,
                **({"must_not": inherited_must_not} if inherited_must_not else {}),
            }
        },
        "aggs": {
            "by_category": {
                "terms": {
                    "field": "category_id",
                    "size": 2000,
                },
                "aggs": {
                    "publications_total": {"sum": {"field": "journal_publications_count"}},
                    "citations_total": {"sum": {"field": "journal_citations_total"}},
                    "citations_mean": {"avg": {"field": "journal_citations_mean"}},
                },
            }
        },
    }

    category_spider = []
    try:
        category_spider_res = es.search(index=index_name, body=category_spider_body)
        category_spider = indicator_parser.parse_category_spider(
            category_spider_res,
            agg_name="by_category",
            limit=12,
        )
    except Exception:
        category_spider = []

    parsed["available_categories"] = available_categories
    parsed["selected_category_id"] = selected_category_id
    parsed["selected_category_level"] = selected_category_level
    parsed["category_publications_spider"] = category_spider
    return parsed, None


def get_indicator_data(data_source_name, filters, study_unit="document"):
    """Orchestrates the retrieval of indicator data from Elasticsearch."""

    filters = filters or {}
    normalized_study_unit = _normalize_indicator_study_unit(study_unit)

    es = get_opensearch_client()
    if not es:
        return None, "Service unavailable"

    data_source = data_sources_with_settings.get_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    breakdown_variable = filters.get("breakdown_variable")

    field_settings = data_source.get("field_settings")

    query = indicator_query.build_query(
        filters,
        field_settings,
        data_source_name,
    )

    aggs = indicator_query.build_indicator_aggs(
        field_settings, breakdown_variable, data_source_name, study_unit=normalized_study_unit
    )

    body = {"size": 0, "query": query, "aggs": aggs}

    try:
        res = es.search(index=data_source.get("index_name"), body=body)
    except Exception:
        return None, "Error executing search"

    data = indicator_parser.parse_indicator_response(
        res,
        breakdown_variable,
        study_unit=normalized_study_unit,
    )
    baseline_filters, comparative_filter_keys = _build_comparison_baseline_filters(filters)
    relative_metrics = {
        "enabled": False,
        "compared_filters": sorted(comparative_filter_keys),
    }

    if comparative_filter_keys:
        baseline_query = indicator_query.build_query(
            baseline_filters,
            field_settings,
            data_source_name,
        )
        baseline_aggs = indicator_query.build_indicator_aggs(
            field_settings,
            None,
            data_source_name,
            study_unit=normalized_study_unit,
        )
        baseline_body = {"size": 0, "query": baseline_query, "aggs": baseline_aggs}

        try:
            baseline_res = es.search(index=data_source.get("index_name"), body=baseline_body)
            baseline_data = indicator_parser.parse_indicator_response(
                baseline_res,
                breakdown_variable=None,
                study_unit=normalized_study_unit,
            )
            relative_metrics = indicator_parser.compute_indicator_relative_metrics(
                data,
                baseline_data,
                study_unit=normalized_study_unit,
            )
            relative_metrics["compared_filters"] = sorted(comparative_filter_keys)
        except Exception:
            relative_metrics = {
                "enabled": False,
                "compared_filters": sorted(comparative_filter_keys),
            }

    data["relative_metrics"] = relative_metrics
    data["study_unit"] = study_unit

    return data, None
