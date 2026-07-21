import time

from django.conf import settings
from django.utils import timezone

from enrichment.models import WorldRegionsStatus, WorldRegionsUpload
from enrichment.world_regions import apply_world_regions, concrete_indices


def empty_stats():
    return {
        "indices": [],
        "total": 0,
        "updated": 0,
        "noops": 0,
        "version_conflicts": 0,
        "failures": 0,
        "took": 0,
        "errors": [],
    }


def task_result(index_name, task_id, response):
    failures = response.get("failures") or []
    errors = []
    for failure in failures[:10]:
        reason = failure.get("cause", {}).get("reason") or failure.get("reason")
        errors.append(reason or str(failure))

    return {
        "index": index_name,
        "task_id": task_id,
        "total": response.get("total", 0),
        "updated": response.get("updated", 0),
        "noops": response.get("noops", 0),
        "version_conflicts": response.get("version_conflicts", 0),
        "failures": len(failures),
        "took": response.get("took", 0),
        "errors": errors,
    }


def add_result(stats, result):
    stats["indices"].append(result)
    for field in (
        "total",
        "updated",
        "noops",
        "version_conflicts",
        "failures",
        "took",
    ):
        stats[field] += result[field]

    stats["errors"].extend(result["errors"])
    stats["errors"] = stats["errors"][:10]

    return stats


def wait_for_task(task_id, poll_interval):
    client = get_opensearch_client()

    while True:
        result = client.tasks.get(task_id=task_id)
        if result.get("completed"):
            if result.get("error"):
                raise RuntimeError(
                    result["error"].get("reason") or str(result["error"])
                )

            return result.get("response") or {}

        time.sleep(poll_interval)


def run_world_regions_upload(
    upload_id,
    alias=None,
    slices=None,
    requests_per_second=None,
    poll_interval=None,
):

    upload = WorldRegionsUpload.objects.get(pk=upload_id)
    alias = alias or settings.ETL_PUBLIC_ALIAS

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

    stats = empty_stats()
    upload.status = WorldRegionsStatus.APPLYING
    upload.current_index = ""
    upload.current_task_id = ""
    upload.stats = stats
    upload.started_at = timezone.now()
    upload.finished_at = None

    upload.save(
        update_fields=[
            "status",
            "current_index",
            "current_task_id",
            "stats",
            "started_at",
            "finished_at",
            "updated",
        ]
    )

    try:
        for index_name in concrete_indices(alias):
            upload.current_index = index_name
            upload.save(update_fields=["current_index", "updated"])
            task_id = apply_world_regions(
                index_name,
                upload.mapping,
                slices=slices,
                requests_per_second=requests_per_second,
            )
            upload.current_task_id = task_id
            upload.save(update_fields=["current_task_id", "updated"])
            response = wait_for_task(task_id, poll_interval)
            
            result = task_result(index_name, task_id, response)
            add_result(stats, result)
            
            upload.stats = stats
            upload.save(update_fields=["stats", "updated"])
            
            if result["failures"] or result["version_conflicts"]:
                raise RuntimeError(
                    f"Falha ao aplicar regiões mundiais em {index_name}."
                )
    except Exception as error:
        stats["errors"].append(str(error))
        stats["errors"] = stats["errors"][:10]

        upload.status = WorldRegionsStatus.FAILED
        upload.current_index = ""
        upload.current_task_id = ""
        upload.stats = stats
        upload.finished_at = timezone.now()

        upload.save(
            update_fields=[
                "status",
                "current_index",
                "current_task_id",
                "stats",
                "finished_at",
                "updated",
            ]
        )
        raise

    upload.status = WorldRegionsStatus.APPLIED
    upload.current_index = ""
    upload.current_task_id = ""
    upload.finished_at = timezone.now()

    upload.save(
        update_fields=[
            "status",
            "current_index",
            "current_task_id",
            "stats",
            "finished_at",
            "updated",
        ]
    )

    return stats
