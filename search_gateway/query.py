from search_gateway.data_sources import get_index_field_name_from_data_source


def query_filters(filters):
    if filters:
        filters_clauses = []
        for f_field, f_value in filters.items():
            if isinstance(f_value, list):
                f_field = get_index_field_name_from_data_source("world", f_field)
                filters_clauses.append({"terms": {f_field: f_value}})
            else:
                filters_clauses.append({"term": {f_field: f_value}})
        return filters_clauses


def build_search_as_you_type_body(field_name, query, agg_size=20):
    """
    Builds the body for a search-as-you-type query.
    """
    return {
        "size": 0,
        "query": {
            "multi_match": {
                "query": query,
                "type": "bool_prefix",
                "fields": [
                    f"{field_name}",
                    f"{field_name}._2gram",
                    f"{field_name}._3gram",
                ],
            }
        },
        "aggs": {
            "unique_items": {
                "terms": {"field": f"{field_name}", "size": agg_size}
            }
        },
    }


def build_term_search_body(field_name, query, aggregation_size=20):
    """
    Builds the body for a term-based search query.
    """
    fn_cleaned = field_name.replace(".keyword", "")

    return {
        "size": 0,
        "query": {"match_phrase_prefix": {fn_cleaned: query}},
        "aggs": {
            "unique_items": {
                "terms": {
                    "field": f"{fn_cleaned}.keyword",
                    "size": aggregation_size,
                }
            }
        },
    }


def build_filters_aggs(field_settings, exclude_fields=None):
    """
    Builds the aggregations for retrieving filter options.
    """
    aggs = {}
    for form_field_name, field_info in field_settings.items():
        if form_field_name in exclude_fields:
            continue
        
        fl_name = field_info.get("index_field_name")
        fl_size = field_info.get("filter", {}).get("size", 1)
        fl_order = field_info.get("order", {}).get("order")
        fl_type = field_info.get("field_type")


        terms = {"field": fl_name, "size": fl_size}
        if fl_order:
            terms["order"] = fl_order

        aggs[form_field_name] = {"terms": terms}
    return aggs


def build_search_text_body(query_text):
    return {
        "query": {
            "simple_query_string": {
                "query": query_text,
                "default_operator": "AND",
            }
        }
    }

def build_document_search_body(
    query_text, filters, page=1, page_size=10, sort_field=None, sort_order="asc", source_fields=None
):
    """
    Builds the body for a document search query with text and filters.
    """
    bool_query = {"must": []}

    if query_text:
        bool_query["must"].append(
            {
                "simple_query_string": {
                    "query": query_text,
                    "default_operator": "AND",
                    "fields": ["title"] # TODO: Definir os fields para a busca
                }
            }
        )
    else:
        bool_query["must"].append({"match_all": {}})

    if filters:
        bool_query["filter"] = query_filters(filters)

    start = (page - 1) * page_size

    body = {
        "from": start,
        "size": page_size,
        "track_total_hits": True,
        "query": {"bool": bool_query},
    }

    if source_fields:
        body["_source"] = source_fields

    if sort_field:
        body["sort"] = [{sort_field: {"order": sort_order}}]

    return body
