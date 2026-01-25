import logging
from urllib.parse import urlencode

from django.utils import timezone

from core.utils.utils import fetch_data
from harvest.exception_logs import ExceptionContext
from harvest.models import HarvestedSciELOData, HarvestErrorLogSciELOData

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)

SEARCH_PATH = "/api/search"
DATASET_PATH = "/api/datasets/:persistentId/"


def _extract_items(payload):
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data.get("items")
        if isinstance(payload.get("items"), list):
            return payload.get("items")
    return []


def _extract_total_count(payload):
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            return data.get("total_count")
    return None


def _build_url(base_url, params):
    return f"{base_url}?{urlencode(params, doseq=True)}"


def fetch_search_page(search_url, start, per_page, headers):
    params = [
        ("q", "*"),
        ("type", "dataset"),
        ("type", "dataverse"),
        ("per_page", per_page),
        ("start", start),
    ]
    url = _build_url(search_url, params)
    payload = fetch_data(url, headers=headers, json=True, timeout=60, verify=True)
    return _extract_items(payload), _extract_total_count(payload)


def fetch_dataset_data(dataset_url, headers, global_id):
    url = _build_url(dataset_url, {"persistentId": global_id})
    payload = fetch_data(url, headers=headers, json=True, timeout=60, verify=True)
    return payload.get("data") if isinstance(payload, dict) else None


def _persist_harvested(user, source_url, identifier, raw_data, type_data):
    harvested_obj, _ = HarvestedSciELOData.objects.get_or_create(
        identifier=identifier,
        creator=user,
    )
    harvested_obj.mark_as_in_progress()
    exc_context = ExceptionContext(
        harvest_object=harvested_obj,
        log_model=HarvestErrorLogSciELOData,
        fk_field="scielo_data",
    )
    try:
        harvested_obj.source_url = source_url
        harvested_obj.type_data = type_data
        harvested_obj.raw_data = raw_data
        harvested_obj.last_harvest_attempt = timezone.now()
        harvested_obj.save(
            update_fields=[
                "source_url",
                "type_data",
                "raw_data",
                "last_harvest_attempt",
            ]
        )
        harvested_obj.mark_as_success()
    except Exception as exc:
        exc_context.add_exception(
            exception=exc,
            field_name="raw_data",
            context_data={"identifier": identifier},
        )
    exc_context.save_to_db()
    exc_context.mark_status_harvest()


def harvest_data(
    user,
    base_url="https://data.scielo.org",
    per_page=100,
    start=None,
    max_pages=None,
):
    search_url = f"{base_url}{SEARCH_PATH}"
    dataset_url = f"{base_url}{DATASET_PATH}"
    total_in_db = HarvestedSciELOData.objects.count()
    start = (
        (total_in_db // 100) * 100 if start is None else start
    )  # Remove dois ultimos numeros
    headers = {"Accept": "text/xml; charset=utf-8", "user-agent": USER_AGENT}
    page_count = 0
    total_count = None
    while True:
        items, total_count = fetch_search_page(
            search_url=search_url, start=start, per_page=per_page, headers=headers
        )

        if not items:
            break

        for item in items:
            item_type = item.get("type")
            if item_type == "dataverse":
                identifier = item.get("identifier")
                if not identifier:
                    logging.warning("Item dataverse sem identifier (start=%s)", start)
                    continue
                _persist_harvested(
                    user=user,
                    source_url=search_url,
                    identifier=identifier,
                    raw_data=item,
                    type_data="dataverse",
                )
            elif item_type == "dataset":
                global_id = item.get("global_id")
                if not global_id:
                    logging.warning("Item dataset sem global_id (start=%s)", start)
                    continue

                data = fetch_dataset_data(
                    dataset_url=dataset_url,
                    global_id=global_id,
                    headers=headers,
                )
                if not data or not data.get("identifier"):
                    logging.warning(
                        "Dataset sem data/identifier (global_id=%s)", global_id
                    )
                    continue
                dataset_source_url = _build_url(
                    dataset_url, {"persistentId": global_id}
                )
                _persist_harvested(
                    user=user,
                    source_url=dataset_source_url,
                    identifier=data.get("identifier"),
                    raw_data=data,
                    type_data="dataset",
                )

        start += per_page
        page_count += 1
        if max_pages and page_count >= max_pages:
            break
        if total_count is not None and start >= total_count:
            break
