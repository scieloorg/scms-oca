from django.conf import settings

from config import celery_app
from etl.models import EtlItemProcess, EtlStatus
from etl.pipeline.defaults import PIPELINE_TARGETS, resolve_target_names
from etl.pipeline.orchestrator import OpenSearchETLPipeline
from etl.services import backfill_bronze_items, process_pending_items

BATCH_SIZE = 1000


# ── Celery tasks ────────────────────────────────────────────────────────────


@celery_app.task(name="[ETL] Run pipeline")
def run_silver_etl(
    target_type="article",
    year=None,
    max_docs=None,
    openalex_index=settings.ETL_RAW_OPENALEX_WORKS,
    user_id=None,
):
    return run_pipeline_targets(
        target_type,
        year=year,
        max_docs=max_docs,
        openalex_index=openalex_index,
    )


@celery_app.task(name="[ETL] Process pending silver items")
def process_pending_silver_etl(limit=BATCH_SIZE, user_id=None, document_type=None):
    """
    Processes one batch of pending ETL items.

    Scheduling is handled by Celery Beat — this task does NOT re-enqueue itself.
    Configure the run interval in the Wagtail admin under Celery > Periodic Tasks.
    """
    return process_pending_items(limit=limit, document_type=document_type)


@celery_app.task(name="[ETL] Retry failed silver ETL items")
def retry_failed_silver_etl(limit=BATCH_SIZE, user_id=None):
    """
    Retries one batch of failed ETL items.

    Scheduling is handled by Celery Beat — this task does NOT re-enqueue itself.
    Configure the run interval in the Wagtail admin under Celery > Periodic Tasks.
    """
    return process_pending_items(limit=limit, retry_failed=True)


# ── Pipeline runner ─────────────────────────────────────────────────────────


def run_pipeline_targets(
    target_type: str,
    *,
    year: int | None = None,
    max_docs: int | None = None,
    openalex_index: str = settings.ETL_RAW_OPENALEX_WORKS,
) -> list[dict]:
    return [
        _run_pipeline_target(
            target_name,
            year=year,
            max_docs=max_docs,
            openalex_index=openalex_index,
        )
        for target_name in resolve_target_names(target_type)
    ]


def _run_pipeline_target(
    target_name: str,
    *,
    year: int | None = None,
    max_docs: int | None = None,
    openalex_index: str = settings.ETL_RAW_OPENALEX_WORKS,
) -> dict:
    target = PIPELINE_TARGETS[target_name]
    pipeline = OpenSearchETLPipeline(
        opensearch_url=getattr(settings, "OS_URL", "http://localhost:9200"),
        bronze_scielo_index=target.bronze_index,
        bronze_openalex_index=openalex_index,
        silver_index_pattern=target.silver_index_pattern,
        public_alias=settings.ETL_PUBLIC_ALIAS,
    )
    result = pipeline.run(
        max_docs=max_docs,
        year_filter=year,
    )
    backfill_bronze_items(target.bronze_index, year=year, limit=max_docs, initial_status=EtlStatus.SUCCESS)
    result["target"] = target_name
    result["public_alias"] = pipeline.public_alias
    result["indexed_indices"] = sorted(pipeline.indexed_index_names)
    return result

