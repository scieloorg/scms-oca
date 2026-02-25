from . import query as query_builder


def apply_search_filters_to_body(body, mapped_filters):
    if not mapped_filters:
        return body

    original_query = body.get("query", {"match_all": {}})

    body_with_filters = dict(body)

    body_with_filters["query"] = {
        "bool": {
            "must": [original_query],
            "filter": query_builder.query_filters(mapped_filters),
        }
    }

    return body_with_filters


def get_mapped_filters(filters, field_settings):
    """
    Map form filter names to Elasticsearch field names.
    
    Args:
        filters: Dict of filters with form field names.
        field_settings: Field settings from data source configuration.
    
    Returns:
        Dict with Elasticsearch field names as keys.
    """
    if not filters:
        return {}
    
    mapped_filters = {}

    for key, value in filters.items():
        if key in field_settings:
            real_field_name = field_settings[key].get("index_field_name")
            mapped_filters[real_field_name] = value

    return mapped_filters


def get_index_field_candidates(index_field_name):
    if not index_field_name:
        return []

    if index_field_name.endswith(".keyword"):
        candidates = [index_field_name, index_field_name[:-8]]
    else:
        candidates = [index_field_name, f"{index_field_name}.keyword"]

    seen = set()
    unique_candidates = []
    
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
    
        seen.add(candidate)
        unique_candidates.append(candidate)

    return unique_candidates


def build_filters_body(aggs, mapped_filters=None):
    body = {"size": 0, "aggs": aggs}

    if mapped_filters:
        body["query"] = {"bool": {"filter": query_builder.query_filters(mapped_filters)}}

    return body
