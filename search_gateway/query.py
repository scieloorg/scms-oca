from .data_sources import get_aggregation_qualified_field_name


def build_search_as_you_type_body(field_name, query, filter_aggregation_type="keyword", aggregation_size=20):
    """
    Builds the body for a search-as-you-type query.
    """
    aggregation_qualified_field_name = get_aggregation_qualified_field_name(
        field_name,
        filter_aggregation_type,
    )

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
                "terms": {
                    "field": aggregation_qualified_field_name,
                    "size": aggregation_size,
                }
            }
        },
    }


def build_term_search_body(field_name, query, filter_aggregation_type="keyword", aggregation_size=20):
    """
    Builds the body for a term-based search query.
    """
    aggregation_qualified_field_name = get_aggregation_qualified_field_name(
        field_name,
        filter_aggregation_type,
    )

    return {
        "size": 0,
        "query": {
            "match_phrase_prefix": {
                field_name: query
            }
        },
        "aggs": {
            "unique_items": {
                "terms": {
                    "field": aggregation_qualified_field_name,
                    "size": aggregation_size,
                }
            }
        },
    }


def build_filters_aggs(field_settings):
    """
    Builds the aggregations for retrieving filter options.
    """
    aggs = {}
    for form_field_name, field_info in field_settings.items():
        fl_name = field_info.get("index_field_name")
        if not fl_name:
            continue

        fl_size = field_info.get("filter", {}).get("size") or 0
        fl_order = field_info.get("filter", {}).get("order") or "asc"
        fl_aggregation_type = field_info.get("filter", {}).get("aggregation_type", "keyword")
        fl_aggregation_qualified_name = get_aggregation_qualified_field_name(fl_name, fl_aggregation_type)

        terms = {
            "field": fl_aggregation_qualified_name,
            "size": fl_size
        }

        if fl_order:
            terms["order"] = fl_order

        aggs[form_field_name] = {"terms": terms}

    return aggs
