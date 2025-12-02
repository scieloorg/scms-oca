from django.utils.translation import gettext as _

def parse_search_item_response(response):
    """
    Parses the response for a search-as-you-type query.
    """
    buckets = response.get("aggregations", {}).get("unique_items", {}).get("buckets", [])
    return [{"key": b["key"], "doc_count": b["doc_count"]} for b in buckets]


def parse_filters_response(response):
    """
    Parses the response for filter aggregations.
    """
    return {
        k: [b["key"] for b in v["buckets"]]
        for k, v in response.get("aggregations", {}).items()
    }


def parse_document_search_response(documents):
    transformed_documents = _transform_document_search_results(documents)
    data_documents = {
        "search_results": transformed_documents,
        "total_results": documents["hits"]["total"]["value"],
    }
    return data_documents


def _transform_document_search_results(search_results):
    transformed_hits = []
    for hit in search_results["hits"]["hits"]:
        transformed_hits.append(
            {
                "index": hit.get("_index"),
                "id": hit.get("_id"),
                "source": hit.get("_source", {}),
                "score": hit.get("_score"),
            }
        )
    return transformed_hits
