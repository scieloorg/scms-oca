from django.conf import settings

from .query import build_lookup_hits_body


def strip_keyword_suffix(field_name):
    if not field_name:
        return ""
    return field_name[:-8] if str(field_name).endswith(".keyword") else str(field_name)


def _resolve_lookup_index_name(lookup_config, data_source):
    return lookup_config.get("index_name") or data_source.index_name


def _resolve_lookup_source_fields(lookup_config):
    return list(
        dict.fromkeys((lookup_config["source_value_field"], lookup_config["source_label_field"]))
    )


def _resolve_lookup_search_fields(lookup_config):
    return list(
        dict.fromkeys(
            (
                lookup_config["search_field"],
                strip_keyword_suffix(lookup_config["search_field"]),
            )
        )
    )


def _read_nested_value(payload, path):
    if payload in (None, "") or not path:
        return None

    current = payload
    for part in str(path).split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    if isinstance(current, list):
        for item in current:
            if item not in (None, ""):
                return item
        return None

    return current


def _normalize_option(value, label=None, doc_count=None):
    if value in (None, ""):
        return None

    option = {"key": str(value), "label": str(label) if label else str(value)}
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
        value = _read_nested_value(source_payload, source_value_field)
        label = _read_nested_value(source_payload, source_label_field)

        option = _normalize_option(value=value, label=label)
        if not option or option["key"] in seen:
            continue
        seen.add(option["key"])
        options.append(option)

    return options


def search_lookup_options(es, data_source, settings_filter, query_text="", filters=None):
    lookup_config = settings_filter.lookup
    if not lookup_config:
        return None, "Lookup not configured"

    lookup_index_name = _resolve_lookup_index_name(lookup_config, data_source)
    search_fields = _resolve_lookup_search_fields(lookup_config)
    sort_field = lookup_config.get("sort_field") or lookup_config["source_label_field"]
    source_fields = _resolve_lookup_source_fields(lookup_config)
    size = settings_filter.get_option_limit(default=100)

    body = build_lookup_hits_body(
        query_text=query_text,
        search_fields=search_fields,
        size=size,
        source_fields=source_fields,
        sort_field=sort_field,
    )

    response = es.search(
        index=lookup_index_name,
        body=body,
        request_timeout=getattr(settings, "OS_REQUEST_TIMEOUT", 40),
    )
    return _parse_lookup_hits(response, lookup_config), None


def search_lookup_options_by_values(es, data_source, settings_filter, values):
    lookup_config = settings_filter.lookup
    if not lookup_config:
        return None, "Lookup not configured"

    normalized_values = [str(value).strip() for value in (values or []) if str(value).strip()]
    if not normalized_values:
        return [], None

    lookup_index_name = _resolve_lookup_index_name(lookup_config, data_source)
    source_value_field = lookup_config["source_value_field"]
    value_field = lookup_config.get("value_field") or source_value_field
    candidate_fields = list(
        dict.fromkeys(
            field_name
            for field_name in (
                value_field,
                strip_keyword_suffix(value_field),
                source_value_field,
                strip_keyword_suffix(source_value_field),
            )
            if field_name
        )
    )

    should_clauses = [{"terms": {field_name: normalized_values}} for field_name in candidate_fields]
    source_fields = _resolve_lookup_source_fields(lookup_config)

    body = {
        "size": max(50, len(normalized_values) * 3),
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        },
    }
    if source_fields:
        body["_source"] = source_fields

    response = es.search(
        index=lookup_index_name,
        body=body,
        request_timeout=getattr(settings, "OS_REQUEST_TIMEOUT", 40),
    )

    options = _parse_lookup_hits(response, lookup_config)
    option_map = {str(option.get("key")): option for option in (options or []) if option.get("key")}
    ordered = []
    for value in normalized_values:
        ordered.append(option_map.get(value) or {"key": value, "label": value})
    return ordered, None
