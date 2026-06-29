from django.conf import settings

from config import celery_app
from core.utils.db import refresh_db_connections
from etl.models import EtlItemProcess, EtlPipelineConfig, EtlResult, EtlStatus
from etl.pipeline import OpenSearchETLPipeline
from etl.services import backfill_input_items, process_pending_items
from search_gateway.freshness import invalidate_freshness_cache


@celery_app.task(name="[ETL] Process pending silver items")
def process_pending_silver_etl(limit=None, user_id=None, document_type=None):
    """
    Processes one batch of pending ETL items.

    Scheduling is handled by Celery Beat — this task does NOT re-enqueue itself.
    Configure the run interval in the Wagtail admin under Celery > Periodic Tasks.
    """
    if limit is None:
        limit = settings.ETL_DEFAULT_BATCH_SIZE
    return process_pending_items(limit=limit, document_type=document_type)


@celery_app.task(name="[ETL] Retry failed silver ETL items")
def retry_failed_silver_etl(limit=None, user_id=None):
    """
    Retries one batch of failed ETL items.

    Scheduling is handled by Celery Beat — this task does NOT re-enqueue itself.
    Configure the run interval in the Wagtail admin under Celery > Periodic Tasks.
    """
    if limit is None:
        limit = settings.ETL_DEFAULT_BATCH_SIZE
    return process_pending_items(limit=limit, retry_failed=True)


def run_pipeline_targets(
    target_type: str,
    *,
    year: int | None = None,
    max_docs: int | None = None,
    openalex_index: str = settings.ETL_OPENALEX_MATCH_INDEX,
) -> list[dict]:
    return [
        _run_pipeline_target(
            target_name,
            year=year,
            max_docs=max_docs,
            openalex_index=openalex_index,
        )
        for target_name in EtlPipelineConfig.objects.resolve_names(target_type)
    ]


def _run_pipeline_target(
    target_name: str,
    *,
    year: int | None = None,
    max_docs: int | None = None,
    openalex_index: str = settings.ETL_OPENALEX_MATCH_INDEX,
) -> dict:
    pipeline_config = EtlPipelineConfig.objects.get_enabled_by_name(target_name)

    pipeline = OpenSearchETLPipeline(
        opensearch_url=getattr(settings, "OS_URL", "http://localhost:9200"),
        input_scielo_index=pipeline_config.input_index,
        input_openalex_index=pipeline_config.openalex_index_for(openalex_index),
        public_alias=settings.ETL_PUBLIC_ALIAS,
        pipeline_config=pipeline_config,
    )

    refresh_db_connections()
    try:
        result = pipeline.run(
            max_docs=max_docs,
            year_filter=year,
        )
    finally:
        refresh_db_connections()

    refresh_db_connections()
    backfill_input_items(
        pipeline_config.input_index,
        year=year,
        limit=max_docs,
        initial_status=EtlStatus.SUCCESS,
    )
    refresh_db_connections()

    openalex_ids = set(result.get("openalex_matched_source_ids") or [])
    dedup_ids = set(result.get("scielo_dedup_source_ids") or [])
    scielo_dedup_map = result.get("scielo_dedup_map") or {}
    openalex_match_map = result.get("openalex_match_map") or {}
    indexed = result.get("total_indexed_docs", 0) > 0

    filters = {
        "source_index": pipeline_config.input_index,
        "document_type": pipeline_config.default_document_type,
        "status": EtlStatus.SUCCESS,
        "result": EtlResult.UNCHANGED,
    }
    if year is not None:
        filters["publication_year"] = year

    items = list(EtlItemProcess.objects.filter(**filters))

    for item in items:
        has_oa = item.external_id in openalex_ids
        has_dedup = item.external_id in dedup_ids
        item.result = (
            EtlResult.MERGED if (has_oa or has_dedup)
            else EtlResult.UPDATED if indexed
            else EtlResult.UNCHANGED
        )
        item.has_openalex_match = has_oa
        item.has_scielo_dedup = has_dedup
        item.scielo_dedup_ids = scielo_dedup_map.get(item.external_id) or []
        item.openalex_match_ids = openalex_match_map.get(item.external_id) or []

    if items:
        refresh_db_connections()
        EtlItemProcess.objects.bulk_update(
            items,
            [
                "result",
                "has_openalex_match",
                "has_scielo_dedup",
                "scielo_dedup_ids",
                "openalex_match_ids",
            ],
            batch_size=getattr(settings, "ETL_ITEM_BULK_UPDATE_BATCH_SIZE", 1000),
        )
        refresh_db_connections()

    result["target"] = target_name
    result["public_alias"] = pipeline.public_alias
    result["indexed_indices"] = sorted(pipeline.indexed_index_names)

    if result.get("total_indexed_docs", 0) > 0:
        invalidate_freshness_cache()

    return result
