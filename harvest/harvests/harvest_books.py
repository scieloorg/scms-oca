import logging
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Max
from django.utils import timezone

from core.utils.utils import fetch_data
from harvest.exception_logs import ExceptionContext
from harvest.indexing import delete_harvested_document
from harvest.models import HarvestedBooks, HarvestErrorLogBooks


def _build_url(base_url, params=None):
    if not params:
        return base_url
    return f"{base_url}?{urlencode(params, doseq=True)}"


def _sanitize_raw_data(payload):
    """
    Muda chave "_id" do payload de books para "id"
    """
    if not isinstance(payload, dict):
        return payload
    if "_id" not in payload:
        return payload
    sanitized = dict(payload)
    sanitized["id"] = sanitized.pop("_id")
    return sanitized


def fetch_doc(base_url, db_name, doc_id, headers, user):
    url = f"{base_url}/{db_name}/{doc_id}"
    try:
        return (
            fetch_data(url, headers=headers, json=True, timeout=60, verify=False),
            url,
        )
    except Exception as exc:
        harvested_obj, _ = HarvestedBooks.objects.get_or_create(
            identifier=doc_id,
            creator=user,
        )
        exc_context = ExceptionContext(
            harvest_object=harvested_obj,
            log_model=HarvestErrorLogBooks,
            fk_field="book",
        )
        exc_context.add_exception(
            exception=exc,
            field_name="fetch_doc",
            context_data={"doc_id": doc_id, "db_name": db_name},
        )
        exc_context.save_to_db()
        exc_context.mark_status_harvest()
        return None, None


def fetch_changes_page(base_url, db_name, since, limit, headers):
    url = _build_url(
        f"{base_url}/{db_name}/_changes",
        {
            "since": since,
        },
    )
    payload = fetch_data(url, headers=headers, json=True, timeout=60, verify=False)
    return payload if isinstance(payload, dict) else {}


def _extract_changes(payload):
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload.get("results")
    return []


def _extract_last_seq(payload):
    if isinstance(payload, dict):
        return payload.get("seq")
    return None


def _persist_harvested_books(
    user,
    source_url,
    identifier,
    raw_data,
    type_data,
    parent=None,
    last_seq=None,
):
    harvested_obj, _ = HarvestedBooks.objects.get_or_create(
        identifier=identifier,
        creator=user,
    )
    harvested_obj.mark_as_in_progress()
    exc_context = ExceptionContext(
        harvest_object=harvested_obj,
        log_model=HarvestErrorLogBooks,
        fk_field="book",
    )
    try:
        harvested_obj.source_url = source_url
        harvested_obj.type_data = type_data
        harvested_obj.parent = parent
        harvested_obj.last_seq = last_seq
        harvested_obj.raw_data = raw_data
        harvested_obj.last_harvest_attempt = timezone.now()
        harvested_obj.save(
            update_fields=[
                "source_url",
                "type_data",
                "parent",
                "last_seq",
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


def _base_url():
    return getattr(settings, "SCIELO_BOOKS_BASE_URL", None)


def _get_last_seq():
    return (
        HarvestedBooks.objects.exclude(last_seq__isnull=True)
        .aggregate(max_seq=Max("last_seq"))
        .get("max_seq")
    )


def _delete_book_record(identifier):
    obj = HarvestedBooks.objects.filter(identifier=identifier).first()
    if obj:
        obj.delete()
        delete_harvested_document(model_name="HarvestedBooks", identifier=identifier)
    return None


def _resolve_monograph_parent(
    base_url,
    db_name,
    monograph_identifier,
    headers,
    user,
):
    parent = HarvestedBooks.objects.filter(identifier=monograph_identifier).first()
    if parent:
        return parent

    monograph_payload, monograph_url = fetch_doc(
        base_url=base_url,
        db_name=db_name,
        doc_id=monograph_identifier,
        headers=headers,
        user=user,
    )
    if not monograph_payload:
        return

    identifier = monograph_payload.get("_id")
    monograph_payload = _sanitize_raw_data(monograph_payload)
    _persist_harvested_books(
        user=user,
        source_url=monograph_url,
        identifier=identifier,
        raw_data=monograph_payload,
        type_data=monograph_payload.get("TYPE"),
    )
    return HarvestedBooks.objects.filter(identifier=identifier).first()


def _include_data_monograph_in_payload_type_part(payload, monograph):
    """
    Insere dados relevantes do livro no payload de capitulo
    """
    monograph_title = monograph.raw_data.get("title")
    monograph_doi = monograph.raw_data.get("doi_number")
    if monograph_title:
        payload["monograph_title"] = monograph_title
    if monograph_doi:
        payload["doi_number"] = monograph_doi
    return payload


def iter_changes(
    db_name="scielobooks_1a",
    since=None,
    limit=100,
    headers=None,
):
    base_url = _base_url()
    if not base_url:
        logging.error("Sem base url definida para coleta de books")
        raise ValueError()

    since = _get_last_seq() if since is None else since
    since = since or 0

    while True:
        payload = fetch_changes_page(
            base_url=base_url,
            db_name=db_name,
            limit=limit,
            since=since,
            headers=headers,
        )
        changes = _extract_changes(payload)
        if not changes:
            break

        for change in changes:
            yield change

        last_seq = _extract_last_seq(payload)
        if last_seq is None or last_seq == since:
            break
        since = last_seq


def harvest_books(
    user,
    db_name="scielobooks_1a",
    limit=100,
    since=None,
    headers=None,
):
    for change in iter_changes(
        db_name=db_name,
        since=since,
        limit=limit,
        headers=headers,
    ):
        harvest_single_book(
            base_url=_base_url(),
            db_name=db_name,
            payload=change,
            headers=headers,
            user=user,
            last_seq=change.get("seq"),
        )


def harvest_single_book(
    base_url,
    db_name,
    payload,
    headers,
    user,
    last_seq=None,
):

    doc_id = payload.get("id")
    if not doc_id:
        return
    if payload.get("deleted"):
        _delete_book_record(identifier=doc_id)
        return
    base_url = _base_url() if not base_url else base_url
    if not base_url:
        logging.error("Sem base url definida para coleta de books")
        raise ValueError()

    payload, doc_url = fetch_doc(
        base_url=base_url,
        db_name=db_name,
        doc_id=doc_id,
        headers=headers,
        user=user,
    )

    identifier = payload.get("_id")
    payload = _sanitize_raw_data(payload)

    type_data = payload.get("TYPE")
    parent = None
    if type_data == "Part":
        parent_identifier = payload.get("monograph")
        if parent_identifier:
            parent = _resolve_monograph_parent(
                base_url=base_url,
                db_name=db_name,
                monograph_identifier=parent_identifier,
                headers=headers,
                user=user,
            )
            if not parent:
                return None
            payload = _include_data_monograph_in_payload_type_part(
                payload=payload, monograph=parent
            )

    _persist_harvested_books(
        user=user,
        source_url=doc_url,
        identifier=identifier,
        raw_data=payload,
        type_data=type_data,
        parent=parent,
        last_seq=last_seq,
    )
