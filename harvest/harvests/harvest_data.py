import logging
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone

from core.utils.utils import fetch_data
from harvest.exception_logs import ExceptionContext
from harvest.models import HarvestedSciELOData, HarvestErrorLogSciELOData

DEFAULT_HEADERS = {"Accept": "text/xml; charset=utf-8", "user-agent": settings.USER_AGENT}

API_SCIELO_DATA = settings.SITE_SCIELO_DATA + "/api/search"
DATASET_URL = settings.SITE_SCIELO_DATA + "/api/datasets/:persistentId/"
DATAVERSE_URL = settings.SITE_SCIELO_DATA + "/api/dataverses/"


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


def fetch_search_page(search_url, start, per_page, headers, type):
    params = [
        ("q", "*"),
        ("type", type),
        ("per_page", per_page),
        ("start", start),
    ]
    url = _build_url(search_url, params)
    payload = fetch_data(url, headers=headers, json=True, timeout=60, verify=True)
    return _extract_items(payload), _extract_total_count(payload)


def fetch_dataset_data(headers, global_id):
    url = _build_url(DATASET_URL, {"persistentId": global_id})
    payload = fetch_data(url, headers=headers, json=True, timeout=60, verify=True)
    return payload.get("data") if isinstance(payload, dict) else None


def fetch_dataverse_data(identifier, headers):
    url = f"{DATAVERSE_URL}{identifier}"
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


def harvest_data(user, type, per_page=100, start=0):
    search_url = API_SCIELO_DATA

    logging.info(f"Iniciando coleta SciELO Data a partir do offset {start}")

    while True:
        try:
            items, total_count = fetch_search_page(
                search_url=search_url,
                type=type,
                start=start,
                per_page=per_page,
                headers=DEFAULT_HEADERS,
            )
        except Exception as exc:
            logging.error(f"Erro ao buscar página (start={start}): {exc}", start, exc)
            break

        if not items:
            logging.info("Nenhum item retornado. Finalizando coleta.")
            break

        for item in items:
            try:
                _persist_item(
                    item=item,
                    user=user,
                )
            except Exception as exc:
                logging.error(f"Erro ao persistir item: {exc}")

        start += per_page
        if total_count is not None and start >= total_count:
            break


def _persist_item(item, user):
    data, source_url, type_data, identifier = _fetch_data_by_type(item)

    _persist_harvested(
        user=user,
        source_url=source_url,
        identifier=identifier,
        raw_data=data,
        type_data=type_data,
    )

def _fetch_data_by_type(item):
    """
    Returns:
        tuple: (data, source_url, type_data, identifier)
    Raises:
        ValueError: If required fields or known types are missing.
    """
    type_data = item.get("type")

    if type_data == "dataverse":
        identifier = item.get("identifier")
        if not identifier:
            raise ValueError("Dataverse sem 'identifier'.")
        data = fetch_dataverse_data(identifier=identifier, headers=DEFAULT_HEADERS)
        source_url = f"{DATAVERSE_URL}{identifier}"
        return data, source_url, type_data, identifier

    elif type_data == "dataset":
        global_id = item.get("global_id")
        if not global_id:
            raise ValueError("Dataset sem 'global_id'.")

        source_url = _build_url(DATASET_URL, {"persistentId": global_id})
        publisher = item.get("publisher")
        dataverse_identifier = item.get("identifier_of_dataverse")
        dataverse_obj = HarvestedSciELOData.objects.filter(identifier=dataverse_identifier).first()
        data = fetch_dataset_data(
            global_id=global_id,
            headers=DEFAULT_HEADERS,
        )
        data["publisher"] = {
            "name": publisher,
            "identifier": dataverse_identifier,
            "url": dataverse_obj.get_url_dataverse
        }
        return data, source_url, type_data, global_id

    else:
        raise ValueError(f"Tipo desconhecido ou não suportado: {type_data}")


def harvest_single_scielo_data(harvested_obj):
    exc_context = ExceptionContext(
        harvest_object=harvested_obj,
        log_model=HarvestErrorLogSciELOData,
        fk_field="scielo_data",
    )

    try:
        data, source_url, type_data, identifier = _fetch_data_by_type({
            "type": harvested_obj.type_data,
            "identifier": harvested_obj.identifier,
        })

        harvested_obj.raw_data = data
        harvested_obj.last_harvest_attempt = timezone.now()
        harvested_obj.save(update_fields=["raw_data", "last_harvest_attempt"])

    except Exception as exc:
        exc_context.add_exception(
            exception=exc,
            field_name="reprocess",
            context_data={
                "identifier": harvested_obj.identifier,
                "type_data": harvested_obj.type_data,
            },
        )

    exc_context.save_to_db()
    exc_context.mark_status_harvest()
