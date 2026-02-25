from search_gateway import data_sources_with_settings

from . import utils


JOURNAL_METRICS_SOURCE_FIELDS = [
    "journal_id",
    "journal_title",
    "journal_issn",
    "publisher_name",
    "country",
    "collection",
    "category_id",
    "category_level",
    "publication_year",
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
    "is_scielo",
    "is_scopus",
    "is_wos",
    "is_doaj",
    "is_openalex",
    "is_journal_multilingual",
]


def build_journal_metrics_query(selected_year, query):
    base_bool = {}

    if query and "bool" in query:
        query_bool = query.get("bool", {})
        must = list(query_bool.get("must", []))
        must_not = list(query_bool.get("must_not", []))
    else:
        must = []
        must_not = []

    if selected_year not in (None, ""):
        try:
            normalized_year = int(selected_year)
        except (TypeError, ValueError):
            normalized_year = selected_year
        must.append({"term": {"publication_year": normalized_year}})

    if must:
        base_bool["must"] = must
    if must_not:
        base_bool["must_not"] = must_not

    return {"bool": base_bool} if base_bool else {"match_all": {}}


def build_journal_metrics_body(selected_year=None, ranking_metric=None, size=500, query=None):
    if not ranking_metric:
        ranking_metric = "journal_impact_normalized"

    return {
        "query": query if query else {"match_all": {}},
        "size": int(size) if str(size).isdigit() else 500,
        "track_total_hits": True,
        "sort": [{ranking_metric: {"order": "desc", "missing": "_last"}}],
        "collapse": {"field": "journal_id"},
        "aggs": {
            "unique_journals": {
                "cardinality": {"field": "journal_id"}
            }
        },
        "_source": JOURNAL_METRICS_SOURCE_FIELDS,
    }


def build_query(filters, field_settings, data_source):
    filters = dict(filters or {})

    social_year_start = None
    social_year_end = None
    if data_source == "social":
        social_year_start = filters.get("document_publication_year_start")
        social_year_end = filters.get("document_publication_year_end")
        filters.pop("document_publication_year_start", None)
        filters.pop("document_publication_year_end", None)
        filters.pop("document_publication_year_range", None)

    translated_filters = utils.translate_fields(filters, field_settings)

    must = []
    must_not = []

    if data_source == "social":
        fl_name = field_settings.get("action", {}).get("index_field_name")
        if fl_name and fl_name.endswith(".keyword"):
            base_field = fl_name.rsplit(".", 1)[0]
            must.append({
                "bool": {
                    "should": [
                        {"exists": {"field": fl_name}},
                        {"exists": {"field": base_field}},
                    ],
                    "minimum_should_match": 1,
                }
            })
        else:
            add_exists(fl_name, must)

        if social_year_start or social_year_end:
            try:
                start_int = int(social_year_start) if social_year_start not in (None, "") else None
            except (TypeError, ValueError):
                start_int = None
            try:
                end_int = int(social_year_end) if social_year_end not in (None, "") else None
            except (TypeError, ValueError):
                end_int = None

            if start_int or end_int:
                created_range = {}
                if start_int:
                    created_range["gte"] = f"{start_int}-01-01"
                if end_int:
                    created_range["lte"] = f"{end_int}-12-31"
                must.append({"range": {"created": created_range}})

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
    """Return a field suitable for cardinality of periodicals."""
    for candidate in ("issn", "journal", "source_name"):
        fl = field_settings.get(candidate, {}).get("index_field_name")
        if fl:
            return fl
    return None


def build_indicator_aggs(field_settings, breakdown_variable, data_source_name, study_unit="document"):
    if study_unit not in ("document", "journal"):
        study_unit = "document"

    cited_by_count_field = field_settings.get("cited_by_count", {}).get("index_field_name")

    periodical_field = None
    if study_unit == "journal":
        periodical_field = _get_periodical_identifier_field(field_settings)

    if data_source_name == "social":
        per_year = {
            "date_histogram": {
                "field": "created",
                "calendar_interval": "year",
                "format": "yyyy",
                "min_doc_count": 1,
            },
            "aggs": {},
        }
    else:
        year_var = "publication_year"
        per_year = {
            "terms": {
                "field": year_var,
                "order": {"_key": "asc"},
                "size": 1000
            },
            "aggs": {},
        }

    aggs = {"per_year": per_year}

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
                if study_unit == "journal" and periodical_field:
                    aggs["per_year"]["aggs"]["breakdown"]["aggs"]["docs_with_citations"]["aggs"] = {
                        "unique_periodicals": {"cardinality": {"field": periodical_field}}
                    }
            elif study_unit == "journal":
                aggs["per_year"]["aggs"]["breakdown"]["aggs"] = {}

            if study_unit == "journal" and periodical_field:
                aggs["per_year"]["aggs"]["breakdown"]["aggs"]["unique_periodicals"] = {
                    "cardinality": {"field": periodical_field}
                }

    return aggs
