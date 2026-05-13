import hashlib
import json
import logging
import traceback
from collections import defaultdict
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from etl.models import EtlItemProcess, EtlResult, EtlStatus
from etl.normalizers import int_or_none
from etl.pipeline.defaults import PipelineTarget, normalize_document_type
from etl.pipeline.orchestrator import SilverETLPipeline
from search_gateway.opensearch import OpenSearchIndexClient

logger = logging.getLogger(__name__)


def clean_source_payload(source: Any) -> Any:
    if isinstance(source, dict) and isinstance(source.get("raw_data"), dict):
        return source["raw_data"]
    if isinstance(source, dict):
        return {
            key: value
            for key, value in source.items()
            if key not in {"oca_indexed_at", "oca_source_hash"}
        }
    return source or {}


def source_hash(source: Any) -> str:
    payload = json.dumps(clean_source_payload(source), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def enqueue_etl_item(
    *,
    source_index: str,
    external_id: str,
    source_payload: dict,
    document_type: str,
    publication_year: int | None = None,
    initial_status: str = EtlStatus.PENDING,
) -> EtlItemProcess:
    payload = clean_source_payload(source_payload)
    current_hash = source_hash(payload)
    resolved_type = normalize_document_type(document_type)
    resolved_year = publication_year or int_or_none(payload.get("publication_year"))
    defaults = {
        "document_type": resolved_type,
        "publication_year": resolved_year,
        "source_hash": current_hash,
        "status": initial_status,
        "result": EtlResult.UNCHANGED if initial_status == EtlStatus.SUCCESS else "",
        "error": None,
    }
    item, created = EtlItemProcess.objects.get_or_create(
        source_index=source_index,
        external_id=external_id,
        defaults=defaults,
    )
    if created:
        return item

    if item.source_hash != current_hash:
        item.document_type = resolved_type
        item.publication_year = resolved_year
        item.source_hash = current_hash
        item.status = EtlStatus.PENDING
        item.result = ""
        item.error = None
        item.processed_at = None
        item.save(
            update_fields=[
                "document_type",
                "publication_year",
                "source_hash",
                "status",
                "result",
                "error",
                "processed_at",
                "updated_at",
            ]
        )
    return item


def backfill_bronze_items(
    *,
    source_index: str,
    document_type: str,
    year: int | None = None,
    limit: int | None = None,
    initial_status: str = EtlStatus.PENDING,
) -> int:
    client = OpenSearchIndexClient()
    if not client.index_exists(source_index):
        logger.warning("Index not found for ETL backfill: %s", source_index)
        return 0

    query: dict[str, Any] = {"match_all": {}}
    if year is not None:
        query = {"bool": {"filter": [{"term": {"publication_year": year}}]}}

    count = 0
    for hit in client.scroll_all(source_index, query=query):
        if limit is not None and count >= limit:
            break
        enqueue_etl_item(
            source_index=source_index,
            external_id=hit["_id"],
            source_payload=hit["_source"],
            document_type=document_type,
            initial_status=initial_status,
        )
        count += 1
    return count


def process_pending_items(
    *,
    source_index: str,
    document_type: str,
    silver_index_pattern: str,
    limit: int = 5000,
    retry_failed: bool = False,
) -> list[dict]:
    statuses = [EtlStatus.PENDING]
    if retry_failed:
        statuses.append(EtlStatus.FAILED)

    with transaction.atomic():
        EtlItemProcess.objects.requeue_stale_processing()
        qs = EtlItemProcess.objects.select_for_update(skip_locked=True).filter(
            source_index=source_index,
            document_type=normalize_document_type(document_type),
            status__in=statuses,
        )
        items = list(qs.order_by("updated_at")[:limit])
        for item in items:
            item.mark_processing()

    groups: dict[int | None, list[EtlItemProcess]] = defaultdict(list)
    for item in items:
        groups[item.publication_year].append(item)

    results = []
    for publication_year, group_items in groups.items():
        try:
            result = process_item_group(
                source_index=source_index,
                document_type=document_type,
                silver_index_pattern=silver_index_pattern,
                publication_year=publication_year,
                items=group_items,
            )
            results.append(result)
            group_result = _resolve_item_result(result)
            for item in group_items:
                item.mark_success(group_result)
        except Exception as exc:
            logger.exception("Silver ETL pending group failed")
            for item in group_items:
                item.mark_failed(exc)
                try:
                    log_etl_error(item=item, exc=exc)
                except Exception:
                    logger.exception("Failed to write ETL error log")
            results.append(
                {
                    "source_index": source_index,
                    "publication_year": publication_year,
                    "errors": len(group_items),
                    "error": str(exc),
                }
            )
    return results


def process_item_group(
    *,
    source_index: str,
    document_type: str,
    silver_index_pattern: str,
    publication_year: int | None,
    items: list[EtlItemProcess],
) -> dict:
    target = PipelineTarget(
        document_type=normalize_document_type(document_type),
        source_index=source_index,
        silver_index_pattern=silver_index_pattern,
    )
    pipeline = SilverETLPipeline(target)
    result = pipeline.run(
        year_filter=publication_year,
        doc_ids=[item.external_id for item in items],
    )
    result["source_index"] = source_index
    result["publication_year"] = publication_year
    result["item_count"] = len(items)
    result["indexed_indices"] = sorted(pipeline.indexed_index_names)

    missing_ids = [
        item.external_id
        for item in items
        if str(item.external_id) not in pipeline.loaded_source_ids
    ]
    if missing_ids:
        result["missing_source_ids"] = missing_ids
        raise RuntimeError(f"Pipeline did not load requested source IDs: {missing_ids}")

    if result.get("errors"):
        raise RuntimeError(f"Pipeline finished with errors: {result}")
    if result.get("total_indexed_docs", 0) <= 0:
        raise RuntimeError(f"Pipeline did not index any silver documents: {result}")
    return result


def _resolve_item_result(result: dict) -> str:
    if result.get("total_indexed_docs", 0):
        return EtlResult.UPDATED
    return EtlResult.UNCHANGED


def log_etl_error(item: EtlItemProcess, exc: Exception):
    client = OpenSearchIndexClient()
    client.client.index(
        index=settings.ETL_ERROR_INDEX,
        body={
            "source_index": item.source_index,
            "external_id": item.external_id,
            "document_type": item.document_type,
            "publication_year": item.publication_year,
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "created_at": timezone.now().isoformat(),
        },
        refresh=False,
    )


__all__ = [
    "backfill_bronze_items",
    "clean_source_payload",
    "enqueue_etl_item",
    "log_etl_error",
    "process_item_group",
    "process_pending_items",
    "source_hash",
]
