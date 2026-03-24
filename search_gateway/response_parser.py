from .utils.transforms import apply_display_transform_from_field_settings


def _get_agg_buckets(response, agg_name):
    return response.get("aggregations", {}).get(agg_name, {}).get("buckets", [])


def _transform_bucket(field_settings, field_name, bucket):
    value = bucket.get("key")
    return {
        "key": value,
        "label": apply_display_transform_from_field_settings(
            field_settings,
            field_name,
            value,
        ),
        "doc_count": bucket.get("doc_count"),
    }


def parse_search_item_response(response, data_source, field_name):
    field_settings = data_source.get_field_settings_dict()
    buckets = _get_agg_buckets(response, "unique_items")
    return [_transform_bucket(field_settings, field_name, bucket) for bucket in buckets]


def parse_filters_response(response, data_source):
    field_settings = data_source.get_field_settings_dict()
    return {
        agg_name: [
            _transform_bucket(field_settings, agg_name, bucket)
            for bucket in _get_agg_buckets(response, agg_name)
        ]
        for agg_name in response.get("aggregations", {})
    }


def parse_terms_agg_keys(response, agg_name):
    if not response or not agg_name:
        return []
    buckets = _get_agg_buckets(response, agg_name)
    return [bucket.get("key") for bucket in buckets if bucket.get("key")]


def parse_document_search_response(documents):
    transformed_documents = _transform_document_search_results(documents)
    return {
        "search_results": transformed_documents,
        "total_results": documents["hits"]["total"]["value"],
    }


def _transform_document_search_results(search_results):
    return [
        {
            "index": hit.get("_index"),
            "id": hit.get("_id"),
            "source": hit.get("_source", {}),
            "score": hit.get("_score"),
        }
        for hit in search_results["hits"]["hits"]
    ]