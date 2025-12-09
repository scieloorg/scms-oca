def query_filters(filters):
    """
    Build filter clauses for Elasticsearch query.

    Note: Filters should already have Elasticsearch field names as keys
    (i.e., already mapped from form field names).

    Args:
        filters: Dict of filters with Elasticsearch field names as keys.

    Returns:
        List of filter clauses for the bool query.
    """
    if not filters:
        return []

    filters_clauses = []
    for f_field, f_value in filters.items():
        if isinstance(f_value, list):
            filters_clauses.append({"terms": {f_field: f_value}})
        else:
            filters_clauses.append({"term": {f_field: f_value}})
    return filters_clauses


def build_search_as_you_type_body(field_name, query, agg_size=20, add_keyword_term=False):
    """
    Builds the body for a search-as-you-type query.

    Args:
        field_name: The Elasticsearch field name to search in.
        query: The search query text.
        agg_size: Maximum number of aggregation results.

    Returns:
        Elasticsearch query body dict.
    """
    agg_field_name = str(field_name)

    if add_keyword_term and not agg_field_name.endswith(".keyword"):
        agg_field_name = f"{agg_field_name}.keyword"

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
                "terms": {"field": agg_field_name, "size": agg_size}
            }
        },
    }


def build_term_search_body(field_name, query, aggregation_size=20):
    """
    Builds the body for a term-based search query.

    Args:
        field_name: The Elasticsearch field name to search in.
        query: The search query text.
        aggregation_size: Maximum number of aggregation results.

    Returns:
        Elasticsearch query body dict.
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

    Args:
        field_settings: Dict of field settings from data source configuration.
        exclude_fields: List of field names to exclude from aggregations.

    Returns:
        Dict of aggregation definitions.
    """
    exclude_fields = exclude_fields or []
    aggs = {}

    for form_field_name, field_info in field_settings.items():
        if form_field_name in exclude_fields:
            continue

        fl_name = field_info.get("index_field_name")
        fl_size = field_info.get("filter", {}).get("size", 1)
        fl_order = field_info.get("filter", {}).get("order")

        terms = {"field": fl_name, "size": fl_size}
        if fl_order:
            terms["order"] = fl_order

        aggs[form_field_name] = {"terms": terms}

    return aggs


def build_search_text_body(query_text):
    """
    Builds a simple text search query body.

    Args:
        query_text: The search query text.

    Returns:
        Elasticsearch query body dict.
    """
    return {
        "query": {
            "simple_query_string": {
                "query": query_text,
                "default_operator": "AND",
            }
        }
    }


def build_document_search_body(
        query_text=None,
        filters=None,
        page=1,
        page_size=10,
        sort_field=None,
        sort_order="asc",
        source_fields=None,
        data_source_name=None,
):
    """
    Builds the body for a document search query with text and filters.

    Args:
        query_text: Text to search for.
        filters: Dict of filters (should already be mapped to ES field names).
        page: Page number (1-based).
        page_size: Number of results per page.
        sort_field: Field to sort by.
        sort_order: Sort order ('asc' or 'desc').
        source_fields: List of fields to include in results.
        data_source_name: Name of the data source (for future use).

    Returns:
        Elasticsearch query body dict.
    """
    bool_query = {"must": []}

    if query_text:
        bool_query["must"].append(
            {
                "simple_query_string": {
                    "query": query_text,
                    "default_operator": "AND",
                    "fields": ["title"],  # TODO: Definir os fields para a busca
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
