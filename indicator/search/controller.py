from search_gateway.client import get_es_client
from search_gateway import data_sources_with_settings

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

    data_source = "journal_metrics"
    data_source_config = data_sources_with_settings.get_data_source(data_source)
    data_source_settings = data_sources_with_settings.get_field_settings(data_source)
    index_name = data_source_config.get("index_name") if data_source_config else None
    if not index_name:
        return None, "Invalid data_source"

    year = form_filters.pop("year", None)
    ranking_metric = form_filters.pop("ranking_metric", "cwts_snip")
    limit = form_filters.pop("limit", 500)
    cleaned_filters = utils.clean_form_filters(form_filters)

    query = indicator_query.build_query(cleaned_filters, data_source_settings, data_source)
    jm_query = indicator_query.build_journal_metrics_query(year, query)

    body = indicator_query.build_journal_metrics_body(
        selected_year=year,
        ranking_metric=ranking_metric,
        query=jm_query,
        size=limit,
    )

    try:
        res = es.search(index=index_name, body=body)
        ranking_data = indicator_parser.parse_journal_metrics_response(
            res, selected_year=year, ranking_metric=ranking_metric
        )
        return ranking_data, None
    except Exception as e:
        return None, f"Error executing search: {e}"


def get_journal_metrics_timeseries(issn=None, journal=None):
    """Fetch per-year series for a single journal from the journal_metrics index."""
    if not issn and not journal:
        return None, "Missing journal identifier"

    es = get_es_client()
    if not es:
        return None, "Service unavailable"

    data_source = "journal_metrics"
    data_source_config = data_sources_with_settings.get_data_source(data_source)
    index_name = data_source_config.get("index_name") if data_source_config else None
    if not index_name:
        return None, "Invalid data_source"

    must = []
    if issn:
        must.append({"term": {"issns.keyword": issn}})
    if journal:
        must.append({"term": {"journal.keyword": journal}})

    body = {
        "size": 1,
        "query": {"bool": {"must": must}},
        "_source": ["journal", "issns", "yearly_info"],
    }

    try:
        res = es.search(index=index_name, body=body)
    except Exception as e:
        return None, f"Error executing search: {e}"

    hits = res.get("hits", {}).get("hits", [])
    if not hits:
        return None, "Not found"

    source = hits[0].get("_source", {})
    return indicator_parser.parse_journal_metrics_timeseries(source), None


def get_indicator_data(data_source_name, filters, study_unit="document"):
    if study_unit == "document_and_citation":
        study_unit = "document"
    """
    Orchestrates the retrieval of indicator data from Elasticsearch.
    """
    es = get_es_client()
    if not es:
        return None, "Service unavailable"

    data_source = data_sources_with_settings.get_data_source(data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    breakdown_variable = filters.get("breakdown_variable")
    if study_unit == "journal":
        breakdown_variable = None

    field_settings = data_source.get("field_settings")

    query = indicator_query.build_query(
        filters,
        field_settings,
        data_source_name,
    )

    aggs = indicator_query.build_indicator_aggs(
        field_settings, breakdown_variable, data_source_name, study_unit=study_unit
    )

    body = {"size": 0, "query": query, "aggs": aggs}

    try:
        res = es.search(index=data_source.get("index_name"), body=body)
    except Exception:
        return None, "Error executing search"

    data = indicator_parser.parse_indicator_response(res, breakdown_variable, study_unit=study_unit)

    data["study_unit"] = study_unit

    return data, None
