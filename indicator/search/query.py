from search_gateway import data_sources

from . import utils


def build_journal_metrics_query(selected_year, query):
    yearly_query = {"bool": {"must": []}}
    if not query or "bool" not in query or "must" not in query["bool"]:
        return yearly_query

    for condition in query["bool"]["must"]:
        if "term" in condition:
            for field, value in condition["term"].items():
                field_stz = field.replace(".keyword", "")
                if field_stz in ("scimago_best_quartile", "openalex_docs_2024_5"):
                    yearly_query["bool"]["must"].append(
                        {"term": {f"yearly_info.{selected_year}.{field_stz}": value}}
                    )
                else:
                    yearly_query["bool"]["must"].append({"term": {field: value}})
    return yearly_query


def build_journal_metrics_body(selected_year=None, ranking_metric=None, size=500, query=None):
    if not selected_year:
        selected_year = "2024"

    if not ranking_metric:
        ranking_metric = "cwts_snip"

    return {
        "query": query if query else {"match_all": {}},
        "size": size,
        "sort": [{f"yearly_info.{selected_year}.{ranking_metric}": {"order": "desc", "missing": 0}}],
        "_source": [
            "journal", "issns", f"yearly_info.{selected_year}.cwts_snip",
            f"yearly_info.{selected_year}.doaj_num_docs", f"yearly_info.{selected_year}.openalex_docs_2024_5",
            f"yearly_info.{selected_year}.scielo_num_docs", f"yearly_info.{selected_year}.scimago_best_quartile",
            f"yearly_info.{selected_year}.scimago_cites_by_doc_2_years", f"yearly_info.{selected_year}.scimago_estimated_apc",
            f"yearly_info.{selected_year}.scimago_estimated_value", f"yearly_info.{selected_year}.scimago_female_authors_percent",
            f"yearly_info.{selected_year}.scimago_overton", f"yearly_info.{selected_year}.scimago_sdg",
            f"yearly_info.{selected_year}.scimago_sjr", f"yearly_info.{selected_year}.scimago_total_cites_3_years",
            f"yearly_info.{selected_year}.scimago_total_docs"
        ]
    }


def build_query(filters, field_settings, data_source):
    translated_filters = utils.translate_fields(filters, field_settings)

    must = []

    if data_source == "brazil":
        add_must_term_to_brazil_data_source(field_settings, must)

    if data_source == "social":
        add_must_term_to_social_data_source(field_settings, must)

    query_operator_fields = data_sources.get_query_operator_fields(data_source)
    index_field_name_to_filter_name_map = data_sources.get_index_field_name_to_filter_name_map(data_source)

    for qualified_index_field_name, value in translated_filters.items():
        index_field_name = data_sources.get_index_field_name_from_qualified_name(qualified_index_field_name)

        filter_name = index_field_name_to_filter_name_map.get(index_field_name)
        if not filter_name:
            continue

        if isinstance(value, list):
            add_must_list(filters, filter_name, qualified_index_field_name, query_operator_fields, value, must)
        else:
            add_must_term(qualified_index_field_name, value, must)

    return {"bool": {"must": must}} if must else {"match_all": {}}


def add_must_list(filters, filter_name, qualified_index_field_name, query_operator_fields, values, must):
    normalized_values = utils.standardize_values(values)
    if not normalized_values:
        return

    operator_value = filters.get(f"{filter_name}_operator")
    if operator_value == "and" and filter_name in query_operator_fields:
        for value in values:
            add_must_term(qualified_index_field_name, value, must)
    else:
        add_must_terms(qualified_index_field_name, values, must)


def add_must_term(name, value, must):
    if value in (None, ""):
        return
    must.append({"term": {name: value}})


def add_must_terms(name, values, must):
    must.append({"terms": {name: values}})


def add_must_term_to_brazil_data_source(field_settings, must):
    fl_name = field_settings.get("country", {}).get("index_field_name")
    fl_aggr_type = field_settings.get("country", {}).get("filter", {}).get("aggregation_type", "keyword")
    fl_qualified_name = data_sources.get_aggregation_qualified_field_name(fl_name, fl_aggr_type)
    must.append({"term": {fl_qualified_name: "BR"}})


def add_must_term_to_social_data_source(field_settings, must):
    fl_name = field_settings.get("action", {}).get("index_field_name")
    fl_aggr_type = field_settings.get("action", {}).get("filter", {}).get("aggregation_type", "keyword")
    fl_qualified_name = data_sources.get_aggregation_qualified_field_name(fl_name, fl_aggr_type)
    must.append({"exists": {"field": fl_qualified_name}})


def build_indicator_aggs(field_settings, breakdown_variable, data_source_name):
    year_var = "publication_year" if data_source_name != "social" else "year"
    cited_by_count_field = field_settings.get("cited_by_count", {}).get("index_field_name")

    aggs = {
        "per_year": {
            "terms": {
                "field": year_var,
                "order": {"_key": "asc"},
                "size": 1000
            },
            "aggs": {},
        }
    }

    if cited_by_count_field:
        aggs["per_year"]["aggs"] = {
            "total_citations": {"sum": {"field": cited_by_count_field}}
        }

    if breakdown_variable:
        breakdown_field_name = field_settings.get(breakdown_variable, {}).get("index_field_name")
        breakdown_aggregation_type = field_settings.get(breakdown_variable, {}).get("filter", {}).get("aggregation_type")

        breakdown_variable_qualified_name = data_sources.get_aggregation_qualified_field_name(
            breakdown_field_name,
            breakdown_aggregation_type,
        )

        if breakdown_field_name:
            aggs["per_year"]["aggs"]["breakdown"] = {
                "terms": {
                    "field": breakdown_variable_qualified_name,
                    "order": {"_key": "asc"},
                    "size": 2500
                },
            }

            if cited_by_count_field:
                aggs["per_year"]["aggs"]["breakdown"]["aggs"] = {"total_citations": {"sum": {"field": cited_by_count_field}}}

    return aggs
