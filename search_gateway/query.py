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
                "terms": {"field": f"{field_name}.keyword", "size": agg_size}
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


def build_filters_aggs(field_settings):
    """
    Builds the aggregations for retrieving filter options.
    """
    aggs = {}
    for form_field_name, field_info in field_settings.items():
        fl_name = field_info.get("index_field_name")
        fl_size = field_info.get("filter", {}).get("size")
        fl_order = field_info.get("filter", {}).get("order")
        fl_type = field_info.get("field_type")

        # Ensure we are using the keyword field for aggregations
        if not fl_name.endswith(".keyword") and fl_type != "keyword":
            name_keyword = f"{fl_name}.keyword"
        else:
            name_keyword = fl_name
        terms = {"field": name_keyword, "size": fl_size}

        if fl_order:
            terms["order"] = fl_order

        aggs[form_field_name] = {"terms": terms}
    return aggs
