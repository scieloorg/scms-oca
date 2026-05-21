import logging
from pathlib import Path

from django.conf import settings

from harvest.global_metrics.opensearch import (
    find_global_metric_group_for_silver_group,
    iter_silver_issn_year_groups,
    update_silver_group_by_query,
)
from search_gateway.client import get_opensearch_client


def apply_global_metrics_upload_to_silver(
    upload_file_id,
    harvest_index=None,
    silver_index=None
):
    from harvest.models import GlobalMetricsUploadFile

    upload_file = GlobalMetricsUploadFile.objects.get(pk=upload_file_id)
    client = get_opensearch_client()
    if client is None:
        raise RuntimeError("Cliente OpenSearch não configurado.")

    harvest_index = harvest_index or settings.GLOBAL_METRICS_FILE_UPLOAD_OPENSEARCH_INDEX
    silver_index = silver_index or getattr(
        settings,
        "ETL_SILVER_INDEX_PATTERN",
        "silver_scientific_production",
    )
    source_file = Path(upload_file.file.name).name

    stats = {
        "upload_file_id": upload_file_id,
        "source_file": source_file,
        "metric_rows": 0,
        "silver_groups_seen": 0,
        "harvest_lookups": 0,
        "groups_processed": 0,
        "matches_found": 0,
        "updated": 0,
        "version_conflicts": 0,
        "unresolved_countries": [],
        "errors": [],
    }
    unresolved_countries = set()

    for silver_group in iter_silver_issn_year_groups(
        client=client,
        silver_index=silver_index,
    ):
        stats["silver_groups_seen"] += 1
        stats["harvest_lookups"] += 1
        group = find_global_metric_group_for_silver_group(
            client=client,
            harvest_index=harvest_index,
            source_file=source_file,
            silver_group=silver_group,
        )
        if group is None:
            continue

        stats["metric_rows"] += group.pop("metric_rows", 0)
        stats["groups_processed"] += 1
        unresolved_countries.update(group.pop("unresolved_countries", []))
        response = update_silver_group_by_query(
            client=client,
            silver_index=silver_index,
            group=group,
        )
        stats["matches_found"] += response.get("total", 0)
        stats["updated"] += response.get("updated", 0)
        stats["version_conflicts"] += response.get("version_conflicts", 0)
        if failures := response.get("failures"):
            stats["errors"].extend(failures)

    stats["unresolved_countries"] = sorted(unresolved_countries)
    logging.info(
        f"Métricas globais do upload {upload_file.pk} aplicadas em {silver_index}: "
        f"{stats['groups_processed']} grupos, {stats['matches_found']} matches, "
        f"{stats['updated']} atualizações."
    )
    return stats
