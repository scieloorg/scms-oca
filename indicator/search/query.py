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
        name = field_settings.get("country", {}).get("index_field_name")
        must.append({"term": {name: "BR"}})
    if data_source == "social":
        name = field_settings.get("action", {}).get("index_field_name")
        must.append({"exists": {"field": name}})

    query_operator_fields = data_sources.get_query_operator_fields(data_source)

    reverse_field_map = {
        setting.get("index_field_name"): key
        for key, setting in field_settings.items()
        if setting.get("index_field_name")
    }

    for field, value in translated_filters.items():
        if isinstance(value, list):
            original_field_name = reverse_field_map.get(field)

            if original_field_name:
                operator_key = f"{original_field_name}_operator"
            else:
                operator_key = f"{field.split('.')[0]}_operator"

            use_and_operator = (
                filters.get(operator_key) == "and"
                and field in query_operator_fields.values()
            )

            normalized_values = sorted(list(set(str(item).strip() for item in value if item)))
            if not normalized_values:
                continue

            if use_and_operator:
                for single_value in normalized_values:
                    must.append({"term": {field: single_value}})
            else:
                must.append({"terms": {field: normalized_values}})
        else:
            if value in (None, ""):
                continue
            must.append({"term": {field: value}})

    return {"bool": {"must": must}} if must else {"match_all": {}}


def build_indicator_aggs(field_settings, breakdown_variable, data_source_name):
    year_var = "publication_year" if data_source_name != "social" else "year"
    cited_by_count_field = field_settings.get("cited_by_count", {}).get("index_field_name")

    aggs = {
        "per_year": {
            "terms": {"field": year_var, "order": {"_key": "asc"}, "size": 1000},
            "aggs": {
                "total_citations": {"sum": {"field": cited_by_count_field}}
            }
        }
    }

    if breakdown_variable:
        breakdown_field = field_settings.get(breakdown_variable, {}).get("index_field_name")
        if breakdown_field:
            aggs["per_year"]["aggs"]["breakdown"] = {
                "terms": {"field": breakdown_field, "order": {"_key": "asc"}, "size": 2500},
                "aggs": {
                    "total_citations": {"sum": {"field": cited_by_count_field}}
                }
            }

    return aggs
