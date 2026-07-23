import logging

from django.conf import settings
from opensearchpy.exceptions import OpenSearchException

from enrichment.exceptions import WorldRegionsProcessingError
from enrichment.models import WorldRegionsUpload
from enrichment.world_regions import (
    apply_world_regions,
    concrete_indices,
    wait_for_task,
)

logger = logging.getLogger(__name__)

AGGREGATED_FIELDS = (
    "total",
    "updated",
    "noops",
    "version_conflicts",
    "failures",
    "took",
)

MAX_STORED_ERRORS = 10


def task_result(index_name, response):
    failures = response.get("failures") or []
    errors = []

    for failure in failures[:MAX_STORED_ERRORS]:
        reason = failure.get("cause", {}).get("reason") or failure.get("reason")
        errors.append(reason or str(failure))

    return {
        "index": index_name,
        "total": response.get("total", 0),
        "updated": response.get("updated", 0),
        "noops": response.get("noops", 0),
        "version_conflicts": response.get("version_conflicts", 0),
        "failures": len(failures),
        "took": response.get("took", 0),
        "errors": errors,
    }


def summarize_results(results, errors=()):
    stats = {
        "indices": list(results),
        **{field: 0 for field in AGGREGATED_FIELDS},
        "errors": [],
    }

    for result in results:
        for field in AGGREGATED_FIELDS:
            stats[field] += result.get(field, 0)

        stats["errors"].extend(result.get("errors") or [])

    stats["errors"].extend(
        str(error)
        for error in errors
        if error
    )
    stats["errors"] = stats["errors"][:MAX_STORED_ERRORS]

    return stats


def record_processing_failure(
    upload,
    results,
    error,
    target_index,
    current_index,
    unexpected=False,
):
    error_type = "Erro inesperado" if unexpected else "Falha"

    logger.exception(
        "%s ao aplicar regiões mundiais: "
        "upload_id=%s target=%s current_index=%s error=%s",
        error_type,
        upload.pk,
        target_index,
        current_index,
        error,
    )

    stats = summarize_results(results, errors=(error,))
    upload.fail_application(stats)


def run_world_regions_upload(
    upload_id,
    alias=None,
    slices=None,
    requests_per_second=None,
    poll_interval=None,
):
    upload = WorldRegionsUpload.objects.get(pk=upload_id)
    target_index = alias or upload.target_index_name

    if slices is None:
        slices = getattr(settings, "WORLD_REGIONS_SLICES", "auto")

    if requests_per_second is None:
        requests_per_second = getattr(
            settings,
            "WORLD_REGIONS_REQUESTS_PER_SECOND",
            -1,
        )

    if poll_interval is None:
        poll_interval = getattr(
            settings,
            "WORLD_REGIONS_TASK_POLL_INTERVAL",
            5,
        )

    results = []
    stats = summarize_results(results)
    current_index = None

    upload.start_application(stats)

    try:
        for current_index in concrete_indices(target_index):
            task_id = apply_world_regions(
                current_index,
                upload.mapping,
                slices=slices,
                requests_per_second=requests_per_second,
            )
            response = wait_for_task(task_id, poll_interval)
            result = task_result(current_index, response)

            results.append(result)
            stats = summarize_results(results)
            upload.update_application_stats(stats)

            if result["failures"] or result["version_conflicts"]:
                raise WorldRegionsProcessingError(
                    f"Falha ao aplicar regiões mundiais em {current_index}: "
                    f"{result['failures']} falha(s) e "
                    f"{result['version_conflicts']} conflito(s) de versão."
                )

    except (OpenSearchException, WorldRegionsProcessingError) as error:
        record_processing_failure(
            upload,
            results,
            error,
            target_index,
            current_index,
        )
        raise

    except Exception as error:
        record_processing_failure(
            upload,
            results,
            error,
            target_index,
            current_index,
            unexpected=True,
        )
        raise

    stats = summarize_results(results)
    upload.complete_application(stats)

    return stats
