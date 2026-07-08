from etl.models import EtlStatus

STATUS_FIELDS = (
    EtlStatus.PENDING,
    EtlStatus.PROCESSING,
    EtlStatus.SUCCESS,
    EtlStatus.FAILED,
    EtlStatus.SKIPPED,
)


def format_document_type_label(document_type):
    return str(document_type).replace("-", " ").replace("_", " ").title()


def build_etl_summary_stats(
    raw_stats,
    enabled_pipeline_document_types,
    source_index_by_document_type=None,
    match_search_index_by_document_type=None,
):
    source_index_by_document_type = {
        **raw_stats.get("source_index_by_type", {}),
        **(source_index_by_document_type or {}),
    }
    match_search_index_by_document_type = match_search_index_by_document_type or {}

    enabled_pipeline_types = set(enabled_pipeline_document_types)
    typed_document_types = (
        set(raw_stats.get("type_counts", {}))
        | set(raw_stats.get("scielo_dedup_counts", {}))
        | set(raw_stats.get("openalex_counts", {}))
    )
    other_document_types = sorted(typed_document_types - enabled_pipeline_types)

    operational_rows = [
        _build_document_type_row(
            document_type,
            raw_stats,
            source_index_by_document_type,
            match_search_index_by_document_type,
        )
        for document_type in enabled_pipeline_document_types
    ]

    other_rows = []
    for document_type in other_document_types:
        row = _build_document_type_row(
            document_type,
            raw_stats,
            source_index_by_document_type,
            match_search_index_by_document_type,
        )
        if row["total"] or row["scielo_dedup"] or row["openalex"]:
            other_rows.append(row)

    return {
        "type_rows": operational_rows + other_rows,
        "enabled_pipeline_document_types": enabled_pipeline_types,
    }


def _build_document_type_row(
    document_type,
    raw_stats,
    source_index_by_document_type,
    match_search_index_by_document_type,
):
    status_by_type = raw_stats.get("type_status_counts", {})
    return {
        "key": document_type,
        "label": format_document_type_label(document_type),
        "source_index": source_index_by_document_type.get(document_type, ""),
        "match_search_index": match_search_index_by_document_type.get(document_type, ""),
        "total": raw_stats.get("type_counts", {}).get(document_type, 0),
        "scielo_dedup": raw_stats.get("scielo_dedup_counts", {}).get(document_type, 0),
        "openalex": raw_stats.get("openalex_counts", {}).get(document_type, 0),
        **{
            status: status_by_type.get((document_type, status), 0)
            for status in STATUS_FIELDS
        },
    }
