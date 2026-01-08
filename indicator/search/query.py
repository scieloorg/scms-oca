from search_gateway import data_sources_with_settings

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
    must_not = []

    if data_source == "brazil":
        fl_name = field_settings.get("country", {}).get("index_field_name")
        add_term(fl_name, "BR", must)

    if data_source == "social":
        fl_name = field_settings.get("action", {}).get("index_field_name")
        add_exists(fl_name, must)

    query_operator_fields = data_sources_with_settings.get_query_operator_fields(data_source)
    index_field_name_to_filter_name_map = data_sources_with_settings.get_index_field_name_to_filter_name_map(data_source)

    for index_field_name, value in translated_filters.items():
        filter_name = index_field_name_to_filter_name_map.get(index_field_name)
        if not filter_name:
            continue

        is_not = filters.get(f"{filter_name}_bool_not") == "true"

        if isinstance(value, list):
            add_list(filters, filter_name, index_field_name, query_operator_fields, value, must)
        else:
            if is_not:
                add_term(index_field_name, value, must_not)
            else:
                add_term(index_field_name, value, must)

    query_bool = {}
    if must:
        query_bool["must"] = must
    if must_not:
        query_bool["must_not"] = must_not

    return {"bool": query_bool} if query_bool else {"match_all": {}}


def add_list(filters, filter_name, qualified_index_field_name, query_operator_fields, values, must):
    normalized_values = utils.standardize_values(values)
    if not normalized_values:
        return

    operator_value = filters.get(f"{filter_name}_operator")
    if operator_value == "and" and filter_name in query_operator_fields:
        for value in values:
            add_term(qualified_index_field_name, value, must)
    else:
        add_terms(qualified_index_field_name, values, must)


def add_exists(name, must):
    if name in (None, ""):
        return
    must.append({"exists": {"field": name}})


def add_term(name, value, must):
    if value in (None, ""):
        return
    must.append({"term": {name: value}})


def add_terms(name, values, must):
    must.append({"terms": {name: values}})


def _get_periodical_identifier_field(field_settings):
    """Return a keyword field suitable for cardinality of periodicals."""
    for candidate in ("issn", "journal", "source_name"):
        fl = field_settings.get(candidate, {}).get("index_field_name")
        if fl:
            if not str(fl).endswith(".keyword"):
                return f"{fl}.keyword"
            return fl
    return None


def build_indicator_aggs(field_settings, breakdown_variable, data_source_name, study_unit="document"):
    if study_unit not in ("document", "journal"):
        study_unit = "document"
    year_var = "publication_year" if data_source_name != "social" else "year"
    cited_by_count_field = field_settings.get("cited_by_count", {}).get("index_field_name")

    periodical_field = None
    if study_unit == "journal":
        periodical_field = _get_periodical_identifier_field(field_settings)

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

        docs_with_citations_agg = {
            "filter": {"range": {cited_by_count_field: {"gt": 0}}}
        }
        if study_unit == "journal" and periodical_field:
            docs_with_citations_agg["aggs"] = {
                "unique_periodicals": {"cardinality": {"field": periodical_field}}
            }
        aggs["per_year"]["aggs"]["docs_with_citations"] = docs_with_citations_agg

    if study_unit == "journal":
        if periodical_field:
            aggs["per_year"]["aggs"]["unique_periodicals"] = {
                "cardinality": {"field": periodical_field}
            }

    if breakdown_variable:
        breakdown_field_name = field_settings.get(breakdown_variable, {}).get("index_field_name")
        if breakdown_field_name:
            aggs["per_year"]["aggs"]["breakdown"] = {
                "terms": {
                    "field": breakdown_field_name,
                    "order": {"_key": "asc"},
                    "size": 2500
                },
            }

            if cited_by_count_field:
                aggs["per_year"]["aggs"]["breakdown"]["aggs"] = {
                    "total_citations": {"sum": {"field": cited_by_count_field}},
                    "docs_with_citations": {
                        "filter": {"range": {cited_by_count_field: {"gt": 0}}}
                    },
                }

    return aggs
