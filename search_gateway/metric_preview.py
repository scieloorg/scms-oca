from typing import Any

from search_gateway.client import get_opensearch_client


def _flatten_mapping_properties(properties, prefix=""):
    fields = set()
    for name, config in (properties or {}).items():
        path = f"{prefix}.{name}" if prefix else name
        fields.add(path)

        subfields = config.get("fields") or {}
        for subfield_name in subfields:
            fields.add(f"{path}.{subfield_name}")

        nested_properties = config.get("properties")
        if nested_properties:
            fields.update(_flatten_mapping_properties(nested_properties, path))
    return fields


def _get_index_mapping_fields(data_source):
    es = get_opensearch_client()
    if not es:
        return set(), "OpenSearch client unavailable"

    try:
        mapping = es.indices.get_mapping(index=data_source.index_name)
    except Exception as exc:
        return set(), str(exc)

    fields = set()
    for index_mapping in mapping.values():
        properties = (index_mapping.get("mappings") or {}).get("properties") or {}
        fields.update(_flatten_mapping_properties(properties))
    return fields, None


def _get_metric_group_config(data_source, study_unit):
    metric_config = data_source.metric_config_schema
    study_units = metric_config.get("study_units") or {}
    group_key = study_unit if study_unit in study_units else None
    if not group_key and study_units:
        group_key = next(iter(study_units.keys()))
    return group_key, study_units.get(group_key) or {}


def _series_preview(years, values, limit=12):
    rows = []
    for year, value in zip(years or [], values or []):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            numeric_value = 0
        if numeric_value:
            rows.append({"year": year, "value": value})

    if rows:
        return rows[-limit:]

    return [
        {"year": year, "value": value}
        for year, value in list(zip(years or [], values or []))[-limit:]
    ]


def build_metric_preview(data_source, study_unit="document") -> dict[str, Any]:
    group_key, group_config = _get_metric_group_config(data_source, study_unit)
    mapping_fields, mapping_error = _get_index_mapping_fields(data_source)

    metrics = []
    for metric in group_config.get("metrics") or []:
        metric_type = metric.get("type", "physical")
        agg = metric.get("agg") or ("computed" if metric_type == "computed" else "count")
        configured_field = metric.get("field")
        resolved_field = None
        field_configured = None
        mapping_found = None
        status = "ok"
        message = ""

        if metric_type == "computed":
            message = metric.get("formula") or ""
        elif agg == "count" or not configured_field:
            message = "Uses bucket doc_count"
        else:
            field_configured = data_source.get_field(configured_field) is not None
            resolved_field = data_source.get_index_field_name(configured_field)
            mapping_found = resolved_field in mapping_fields if mapping_fields else None

            if not field_configured:
                status = "warning"
                message = "Field key is not configured in DataSource field_settings"
            if mapping_found is False:
                status = "error"
                message = "Resolved OpenSearch field was not found in index mapping"
            elif not message:
                message = "Resolved field exists in OpenSearch mapping"

        metrics.append(
            {
                "key": metric.get("key"),
                "type": metric_type,
                "agg": agg,
                "configured_field": configured_field,
                "resolved_field": resolved_field,
                "field_configured": field_configured,
                "mapping_found": mapping_found,
                "status": status,
                "message": message,
            }
        )

    charts = []
    data = None
    data_error = None
    try:
        from indicator.metrics.controller import get_indicator_data

        data, data_error = get_indicator_data(data_source.index_name, {}, group_key or study_unit)
    except Exception as exc:
        data_error = str(exc)

    if data:
        for chart in data.get("charts") or []:
            chart_rows = []
            for series in chart.get("series") or []:
                values = series.get("data") or []
                chart_rows.append(
                    {
                        "name": series.get("name"),
                        "total": sum(float(value or 0) for value in values),
                        "preview": _series_preview(chart.get("years") or data.get("years"), values),
                    }
                )
            charts.append(
                {
                    "id": chart.get("id"),
                    "title": chart.get("title"),
                    "series": chart_rows,
                }
            )

    return {
        "study_unit": group_key,
        "mapping_error": mapping_error,
        "metrics": metrics,
        "charts": charts,
        "data_error": data_error,
    }
