import logging

from django.contrib.auth import get_user_model

from config import celery_app
from harvest.harvests.harvest_books import (
    harvest_books,
    harvest_single_book,
    iter_changes,
)
from harvest.harvests.harvest_data import harvest_data
from harvest.harvests.harvest_preprint import harvest_preprint

from .indexing import delete_harvested_document
from .models import HarvestedBooks, HarvestedPreprint
from .service import service_oai_pmh_scythe, service_oai_pmh_sickle

User = get_user_model()


def get_latest_preprint():
    # Recupera o ultimo registro de Preprint a partir do header.datestamp armazenado no campo datestamp
    try:
        return HarvestedPreprint.objects.latest("datestamp")
    except HarvestedPreprint.DoesNotExist:
        return None


def transform_verify_in_python(verify_value):
    """
    Transforma o valor de 'verify' vindo do JSON (string/bool) para bool Python verdadeiro.
    Aceita True/False, "true"/"false", 1/0, "1"/"0".
    """
    if isinstance(verify_value, bool):
        return verify_value
    if isinstance(verify_value, str):
        return verify_value.strip().lower() in ("true", "1")
    return False


@celery_app.task(name="Harvest data preprint")
def harvest_preprint_in_endpoint_oai_pmh(username, user_id=None, url=None, verify=True):
    user = User.objects.get(username=username)
    verify = transform_verify_in_python(verify_value=verify)
    url = url or "https://preprints.scielo.org/index.php/scielo/oai"
    latest_preprint = get_latest_preprint()
    from_date = latest_preprint.datestamp.date().__str__() if latest_preprint else None
    logging.info(f"Coleta a partir da data {from_date}")
    recs = service_oai_pmh_scythe(url=url, from_date=from_date, verify=verify)
    harvest_preprint(recs=recs, user=user)


@celery_app.task(name="Harvest data SciELO Data")
def harvest_scielo_data_in_endpoint_dataverse(
    username,
    user_id=None,
    base_url=None,
    per_page=100,
    start=None,
):
    user = User.objects.get(username=username)
    base_url = base_url or "https://data.scielo.org"
    harvest_data(
        user=user,
        base_url=base_url,
        per_page=per_page,
        start=start,
    )


@celery_app.task(name="Harvest Books")
def harvest_books_in_couchdb(
    username,
    user_id=None,
    limit=100,
    start=None,
    since=None,
    db_name="scielobooks_1a",
    max_pages=None,
    headers=None,
    run_single_tasks=True,
):
    user = User.objects.get(username=username)
    since = start if since is None else since
    if not run_single_tasks:
        harvest_books(
            user=user,
            limit=limit,
            since=since,
            db_name=db_name,
            headers=headers,
        )
        return

    for change in iter_changes(
        db_name=db_name,
        since=since,
        limit=limit,
        headers=headers,
    ):
        doc_id = change.get("id")
        if not doc_id:
            continue
        harvest_single_book_in_couchdb.delay(
            username=username,
            doc_id=doc_id,
            db_name=db_name,
            headers=headers,
        )


@celery_app.task(name="Harvest Single Book")
def harvest_single_book_in_couchdb(
    username,
    doc_id,
    user_id=None,
    db_name="scielobooks_1a",
    headers=None,
):
    user = User.objects.get(username=username)
    harvest_single_book(
        base_url=None,
        doc_id=doc_id,
        db_name=db_name,
        user=user,
        headers=headers,
    )
