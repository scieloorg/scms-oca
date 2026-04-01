from .transforms import (
    apply_display_transform,
    apply_display_transform_from_field_settings,
)


def _get_agg_buckets(response, agg_name):
    return response.get("aggregations", {}).get(agg_name, {}).get("buckets", [])


def _transform_bucket(field_settings, field_name, bucket):
    value = bucket.get("key")
    return {
        "value": value,
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


def _hits_total_value(response):
    total = (response.get("hits") or {}).get("total")
    if total is None:
        return None
    if isinstance(total, dict):
        return total.get("value")
    try:
        return int(total)
    except (TypeError, ValueError):
        return None


def parse_aggregation_response(response, parse_config):
    """
    Pivot nested terms aggregations (e.g. country -> year) for observation table.

    parse_config:
        row_agg_name, col_agg_name (required),
        data_source (optional),
        row_field_name (optional, for labels),
        row_display_transform (optional; bypasses field_settings transform),
    """
    parse_config = dict(parse_config or {})
    data_source = parse_config.get("data_source")
    row_agg_name = parse_config["row_agg_name"]
    col_agg_name = parse_config["col_agg_name"]
    row_field_name = parse_config.get("row_field_name", row_agg_name)
    row_transform_override = parse_config.get("row_display_transform")

    field_settings = (
        data_source.get_field_settings_dict() if data_source else {}
    )

    row_buckets = _get_agg_buckets(response, row_agg_name)
    col_keys = set()
    for rb in row_buckets:
        for cb in (rb.get(col_agg_name) or {}).get("buckets", []) or []:
            key = cb.get("key")
            if key is not None:
                col_keys.add(key)

    def _col_sort_key(key):
        try:
            return (0, int(key))
        except (TypeError, ValueError):
            return (1, str(key))

    columns = [str(c) for c in sorted(col_keys, key=_col_sort_key)]

    rows = []
    for rb in row_buckets:
        raw_key = rb.get("key")
        if row_transform_override:
            label = apply_display_transform(row_transform_override, raw_key)
        else:
            label = apply_display_transform_from_field_settings(
                field_settings,
                row_field_name,
                raw_key,
            )
        values = {}
        for cb in (rb.get(col_agg_name) or {}).get("buckets", []) or []:
            ck = cb.get("key")
            if ck is None:
                continue
            values[str(ck)] = cb.get("doc_count", 0)
        rows.append({"key": raw_key, "label": label, "values": values})

    grand_total = _hits_total_value(response)
    if grand_total is None:
        grand_total = sum(rb.get("doc_count", 0) for rb in row_buckets)

    return {
        "columns": columns,
        "rows": rows,
        "grand_total": grand_total,
    }


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
