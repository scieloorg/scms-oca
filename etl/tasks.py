from django.conf import settings

from config import celery_app
from etl.models import EtlStatus
from etl.pipeline.defaults import PipelineTarget
from etl.pipeline.orchestrator import SilverETLPipeline
from etl.services import backfill_bronze_items, process_pending_items


@celery_app.task(name="[ETL] Run explicit Silver pipeline")
def run_silver_etl(
    *,
    source_index: str,
    document_type: str,
    silver_index_pattern: str,
    year: int | None = None,
    max_docs: int | None = None,
    user_id=None,
):
    target = PipelineTarget(
        document_type=document_type,
        source_index=source_index,
        silver_index_pattern=silver_index_pattern,
    )
    pipeline = SilverETLPipeline(
        target,
        opensearch_url=getattr(settings, "OS_URL", "http://localhost:9200"),
    )
    result = pipeline.run(max_docs=max_docs, year_filter=year)
    result["indexed_indices"] = sorted(pipeline.indexed_index_names)
    return result


@celery_app.task(name="[ETL] Backfill explicit Silver items")
def backfill_silver_etl_items(
    *,
    source_index: str,
    document_type: str,
    year: int | None = None,
    limit: int | None = None,
    user_id=None,
):
    return backfill_bronze_items(
        source_index=source_index,
        document_type=document_type,
        year=year,
        limit=limit,
        initial_status=EtlStatus.PENDING,
    )


@celery_app.task(name="[ETL] Process explicit pending Silver items")
def process_pending_silver_etl(
    *,
    source_index: str,
    document_type: str,
    silver_index_pattern: str,
    limit: int | None = None,
    user_id=None,
):
    return process_pending_items(
        source_index=source_index,
        document_type=document_type,
        silver_index_pattern=silver_index_pattern,
        limit=limit or settings.ETL_DEFAULT_BATCH_SIZE,
    )


@celery_app.task(name="[ETL] Retry explicit failed Silver items")
def retry_failed_silver_etl(
    *,
    source_index: str,
    document_type: str,
    silver_index_pattern: str,
    limit: int | None = None,
    user_id=None,
):
    return process_pending_items(
        source_index=source_index,
        document_type=document_type,
        silver_index_pattern=silver_index_pattern,
        limit=limit or settings.ETL_DEFAULT_BATCH_SIZE,
        retry_failed=True,
    )
