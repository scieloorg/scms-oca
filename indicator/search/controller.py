from search_gateway.client import get_es_client
from search_gateway import data_sources

from . import query as indicator_query
from . import parser as indicator_parser
from . import utils


def get_journal_metrics_data(form_filters):
    """
    Orchestrates the retrieval of journal metrics data.
    """
    es = get_es_client()
    if not es:
        return None, "Service unavailable"

    data_source_name = "journal_metrics"
    data_source = data_sources.DATA_SOURCES[data_source_name]

    year = form_filters.pop("year", None)
    ranking_metric = form_filters.pop("ranking_metric", "cwts_snip")
    limit = form_filters.pop("limit", 500)
    cleaned_filters = utils.clean_form_filters(form_filters)

    field_settings = data_source.get("field_settings")
    query = indicator_query.build_query(cleaned_filters, field_settings, data_source_name)
    jm_query = indicator_query.build_journal_metrics_query(year, query)

    body = indicator_query.build_journal_metrics_body(
        selected_year=year,
        ranking_metric=ranking_metric,
        query=jm_query,
        size=limit,
    )

    try:
        res = es.search(index=data_source.get("index_name"), body=body)
        ranking_data = indicator_parser.parse_journal_metrics_response(
            res, selected_year=year, ranking_metric=ranking_metric
        )
        return ranking_data, None
    except Exception as e:
        return None, f"Error executing search: {e}"


def get_indicator_data(data_source_name, filters):
    """
    Orchestrates the retrieval of indicator data from Elasticsearch.
    """
    es = get_es_client()
    if not es:
        return None, "Service unavailable"

    data_source = data_sources.DATA_SOURCES.get(data_source_name)
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
        field_settings, breakdown_variable, data_source_name
    )

    body = {"size": 0, "query": query, "aggs": aggs}

    try:
        res = es.search(index=data_source.get("index_name"), body=body)
    except Exception:
        return None, "Error executing search"

    data = indicator_parser.parse_indicator_response(res, breakdown_variable)

    return data, None
