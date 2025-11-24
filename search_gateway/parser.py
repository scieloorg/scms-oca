def parse_search_item_response(response):
    """
    Parses the response for a search-as-you-type query.
    """
    buckets = response.get("aggregations", {}).get("unique_items", {}).get("buckets", [])
    return [{"id": b["key"], "text": b["key"]} for b in buckets]


def parse_filters_response(response):
    """
    Parses the response for filter aggregations.
    """
    return {
        k: [b["key"] for b in v["buckets"]]
        for k, v in response.get("aggregations", {}).items()
    }
