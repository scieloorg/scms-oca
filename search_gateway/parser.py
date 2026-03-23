from . import transforms


def _transform_bucket(field_settings, field_name, bucket):
    value = bucket.get("key")
    return {
        "key": value,
        "label": transforms.apply_display_transform_from_field_settings(
            field_settings,
            field_name,
            value,
        ),
        "doc_count": bucket.get("doc_count"),
    }


def parse_search_item_response_with_transform(response, data_source, field_name):
    field_settings = data_source.get_field_settings_dict()
    buckets = response.get("aggregations", {}).get("unique_items", {}).get("buckets", [])
    return [_transform_bucket(field_settings, field_name, bucket) for bucket in buckets]


def parse_filters_response_with_transform(response, data_source):
    field_settings = data_source.get_field_settings_dict()
    return {
        agg_name: [
            _transform_bucket(field_settings, agg_name, bucket)
            for bucket in agg_data.get("buckets", [])
        ]
        for agg_name, agg_data in response.get("aggregations", {}).items()
    }


def parse_search_item_response(response, data_source, field_name):
    return parse_search_item_response_with_transform(response, data_source, field_name)


def parse_terms_agg_keys(response, agg_name):
    if not response or not agg_name:
        return []
    buckets = response.get("aggregations", {}).get(agg_name, {}).get("buckets", [])
    return [bucket.get("key") for bucket in buckets if bucket.get("key")]


def parse_filters_response(response, data_source):
    return parse_filters_response_with_transform(response, data_source)


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
