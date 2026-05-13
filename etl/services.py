import logging
import traceback
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from etl.client import OpenSearchClient
from etl.models import EtlItemProcess, EtlPipelineConfig, EtlResult, EtlStatus
from etl.pipeline import OpenSearchETLPipeline
from etl.transform.extractors import extract_isbns
from harvest.utils import clean_source_payload, source_hash

logger = logging.getLogger(__name__)


def enqueue_etl_item(
    *,
    source_index: str,
    external_id: str,
    source_payload: dict,
    document_type: str | None = None,
    publication_year: int | None = None,
    initial_status: str = EtlStatus.PENDING,
) -> EtlItemProcess:
    current_hash = source_hash(source_payload)
    pipeline_config = EtlPipelineConfig.objects.get_for_source(source_index, source_payload)
    resolved_type = document_type or pipeline_config.document_type_for_payload(source_payload)
    resolved_year = publication_year or _extract_publication_year(source_payload)

    raw_ids = source_payload.get("ids") if isinstance(source_payload.get("ids"), dict) else {}
    pid_v2 = (
        source_payload.get("pid_v2")
        or source_payload.get("code")
        or raw_ids.get("scl_preprint_id")
        or raw_ids.get("dataset_id")
        or ""
    )
    doi = source_payload.get("doi") or raw_ids.get("doi") or ""
    isbns = extract_isbns(source_payload)
    isbn = isbns[0] if isbns else ""
    preprint_id = raw_ids.get("scl_preprint_id") or ""
    dataset_id = raw_ids.get("dataset_id") or ""

    defaults = {
        "document_type": resolved_type,
        "publication_year": resolved_year,
        "source_hash": current_hash,
        "status": initial_status,
        "result": EtlResult.UNCHANGED if initial_status == EtlStatus.SUCCESS else "",
        "error": None,
        "pid_v2": pid_v2,
        "doi": doi,
        "isbn": isbn,
        "preprint_id": preprint_id,
        "dataset_id": dataset_id,
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
        item.pid_v2 = pid_v2
        item.doi = doi
        item.isbn = isbn
        item.preprint_id = preprint_id
        item.dataset_id = dataset_id
        item.status = EtlStatus.PENDING
        item.result = ""
        item.error = None
        item.processed_at = None
        item.save(
            update_fields=[
                "document_type",
                "publication_year",
                "source_hash",
                "pid_v2",
                "doi",
                "isbn",
                "preprint_id",
                "dataset_id",
                "status",
                "result",
                "error",
                "processed_at",
                "updated_at",
            ]
        )

    return item


def _extract_publication_year(source_payload: dict) -> int | None:
    payload = clean_source_payload(source_payload)
    value = payload.get("publication_year")

    if value is None and payload.get("year") is not None:
        value = payload.get("year")

    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def backfill_input_items(
    input_index: str,
    *,
    year: int | None = None,
    limit: int | None = None,
    initial_status: str = EtlStatus.PENDING,
) -> int:
    client = OpenSearchClient()

    if not client.index_exists(input_index):
        logger.warning("Index not found for backfill: %s", input_index)
        return 0

    query: dict = {"match_all": {}}
    if year is not None:
        query = {"bool": {"filter": [{"term": {"publication_year": year}}]}}

    page_size = min(limit, 1000) if limit else 1000
    search_body = {"query": query, "size": page_size}

    count = 0
    response = client.client.search(index=input_index, body=search_body, scroll="5m")
    scroll_id = response.get("_scroll_id")

    try:
        while True:
            hits = response["hits"]["hits"]
            if not hits:
                break

            for hit in hits:
                if limit is not None and count >= limit:
                    break

                enqueue_etl_item(
                    source_index=input_index,
                    external_id=hit["_id"],
                    source_payload=hit["_source"],
                    initial_status=initial_status,
                )
                count += 1

            if limit is not None and count >= limit:
                break

            response = client.client.scroll(scroll_id=scroll_id, scroll="5m")
            scroll_id = response.get("_scroll_id")

    finally:
        if scroll_id:
            client.client.clear_scroll(scroll_id=scroll_id)

    logger.info(
        "Backfilled %s items from %s (status=%s)",
        count,
        input_index,
        initial_status,
    )
    return count


def process_pending_items(
    limit: int = 5000,
    retry_failed: bool = False,
    document_type: str | None = None,
) -> list[dict]:
    statuses = [EtlStatus.PENDING]
    if retry_failed:
        statuses.append(EtlStatus.FAILED)

    with transaction.atomic():
        EtlItemProcess.objects.requeue_stale_processing()

        qs = EtlItemProcess.objects.select_for_update(skip_locked=True).filter(
            status__in=statuses
        )
        if document_type:
            qs = qs.filter(document_type=document_type)

        items = list(qs.order_by("updated_at")[:limit])
        for item in items:
            item.mark_processing()

    groups: dict[tuple[str, int | None, str], list[EtlItemProcess]] = defaultdict(list)
    for item in items:
        groups[(item.source_index, item.publication_year, item.document_type)].append(item)

    results = []
    for (source_index, year, item_document_type), group_items in groups.items():
        try:
            result = process_item_group(source_index, year, item_document_type, group_items)
            results.append(result)

            openalex_ids = set(result.get("openalex_matched_source_ids") or [])
            dedup_ids = set(result.get("scielo_dedup_source_ids") or [])
            scielo_dedup_map = result.get("scielo_dedup_map") or {}
            openalex_match_map = result.get("openalex_match_map") or {}
            indexed = result.get("total_indexed_docs", 0) > 0

            for item in group_items:
                has_oa = item.external_id in openalex_ids
                has_dedup = item.external_id in dedup_ids
                item_result = (
                    EtlResult.MERGED if (has_oa or has_dedup)
                    else EtlResult.UPDATED if indexed
                    else EtlResult.UNCHANGED
                )
                item.mark_success(
                    item_result,
                    has_openalex_match=has_oa,
                    has_scielo_dedup=has_dedup,
                    scielo_dedup_ids=scielo_dedup_map.get(item.external_id) or [],
                    openalex_match_ids=openalex_match_map.get(item.external_id) or [],
                )

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
                    "publication_year": year,
                    "errors": len(group_items),
                    "error": str(exc),
                }
            )

    return results


def process_item_group(
    source_index: str,
    publication_year: int | None,
    document_type: str,
    items: list[EtlItemProcess],
) -> dict:
    source_payload = {"type": document_type}
    config_name = EtlPipelineConfig.objects.resolve_name_for_source(
        source_index,
        source_payload,
    )
    if not config_name:
        raise ValueError(f"No ETL target configured for source index: {source_index}")

    pipeline_config = EtlPipelineConfig.objects.get_for_source(source_index, source_payload)

    pipeline = OpenSearchETLPipeline(
        input_scielo_index=source_index,
        input_openalex_index=pipeline_config.openalex_index,
        silver_index_pattern=pipeline_config.silver_index_pattern,
        public_alias=settings.ETL_PUBLIC_ALIAS,
        pipeline_config=pipeline_config,
    )

    result = pipeline.run(
        year_filter=publication_year,
        doc_ids=[item.external_id for item in items],
    )

    result["source_index"] = source_index
    result["publication_year"] = publication_year
    result["document_type"] = document_type
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


def log_etl_error(item: EtlItemProcess, exc: Exception):
    client = OpenSearchClient()
    client.client.index(
        index="etl_errors",
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
