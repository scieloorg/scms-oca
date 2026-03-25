from .query import build_lookup_hits_body


def _normalize_option(value, label=None, doc_count=None):
    if value in (None, ""):
        return None

    normalized_value = str(value)
    normalized_label = str(label if label not in (None, "") else normalized_value)
    option = {"value": normalized_value, "label": normalized_label}
    if doc_count is not None:
        option["doc_count"] = doc_count
    return option


def _parse_lookup_hits(response, lookup_config):
    hits = response.get("hits", {}).get("hits", [])
    options = []
    seen = set()

    source_value_field = lookup_config["source_value_field"]
    source_label_field = lookup_config["source_label_field"]

    for hit in hits:
        source_payload = hit.get("_source", {}) or {}
        value = source_payload.get(source_value_field)
        label = source_payload.get(source_label_field)

        option = _normalize_option(value=value, label=label)
        if not option or option["value"] in seen:
            continue
        seen.add(option["value"])
        options.append(option)

    return options


def search_lookup_options(client, settings_filter, query_text="", request_timeout=40):
    lookup_config = settings_filter.lookup

    lookup_index_name = lookup_config["index_name"]
    search_fields = [lookup_config["search_field"]]
    sort_field = lookup_config["sort_field"]
    source_fields = [lookup_config["source_value_field"], lookup_config["source_label_field"]]
    size = settings_filter.get_option_limit(default=100)

    body = build_lookup_hits_body(
        query_text=query_text,
        search_fields=search_fields,
        size=size,
        source_fields=source_fields,
        sort_field=sort_field,
    )

    response = client.search(
        index=lookup_index_name,
        body=body,
        request_timeout=request_timeout,
    )

    return _parse_lookup_hits(response, lookup_config), None


def search_lookup_options_by_values(client, settings_filter, values, request_timeout=40):
    lookup_config = settings_filter.lookup

    normalized_values = [str(value).strip() for value in (values or []) if str(value).strip()]
    if not normalized_values:
        return [], None

    lookup_index_name = lookup_config["index_name"]
    value_field = lookup_config["value_field"]
    source_fields = [lookup_config["source_value_field"], lookup_config["source_label_field"]]

    body = {
        "size": max(50, len(normalized_values) * 3),
        "query": {"terms": {value_field: normalized_values}},
    }
    if source_fields:
        body["_source"] = source_fields

    response = client.search(
        index=lookup_index_name,
        body=body,
        request_timeout=request_timeout,
    )

    options = _parse_lookup_hits(response, lookup_config)
    option_map = {option["value"]: option for option in (options or []) if option.get("value")}
    ordered = []
    for value in normalized_values:
        ordered.append(option_map.get(value) or {"value": value, "label": value})
    return ordered, None
