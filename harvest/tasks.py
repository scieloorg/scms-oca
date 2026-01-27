import logging

from django.contrib.auth import get_user_model

from config import celery_app
from harvest.exception_logs import ExceptionContext
from harvest.harvests.harvest_books import (
    harvest_books,
    harvest_single_book,
    iter_changes,
)
from harvest.harvests.harvest_data import harvest_data, harvest_single_scielo_data
from harvest.harvests.harvest_preprint import harvest_preprint
from harvest.indexing import index_harvested_instance

from .models import (
    HarvestedBooks,
    HarvestedPreprint,
    HarvestedSciELOData,
    HarvestErrorLogPreprint,
    HarvestStatus,
    IndexStatus,
)
from .service import service_oai_pmh_get_record, service_oai_pmh_scythe

User = get_user_model()


@celery_app.task(name="Harvest data preprint")
def harvest_preprint_in_endpoint_oai_pmh(username, user_id=None, url=None, verify=True):
    user = User.objects.get(username=username)
    url = url or "https://preprints.scielo.org/index.php/scielo/oai"
    latest_preprint = HarvestedPreprint.get_latest_preprint()
    from_date = latest_preprint.datestamp.date().__str__() if latest_preprint else None
    logging.info(f"Coleta a partir da data {from_date}")
    recs = service_oai_pmh_scythe(url=url, from_date=from_date, verify=verify)
    harvest_preprint(recs=recs, user=user)


@celery_app.task(name="Harvest data SciELO Data")
def harvest_scielo_data_in_endpoint_dataverse(
    username,
    user_id=None,
    per_page=100,
    start=None,
):
    user = User.objects.get(username=username)
    harvest_data(user=user, per_page=per_page, start=start)


@celery_app.task(name="Harvest Books")
def harvest_books_in_couchdb(
    username,
    user_id=None,
    limit=100,
    start=None,
    since=None,
    db_name="scielobooks_1a",
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


@celery_app.task(name="Retry failed preprints")
def retry_failed_preprints_oai_pmh(username, user_id=None, url=None, verify=True):
    user = User.objects.get(username=username)
    url = url or "https://preprints.scielo.org/index.php/scielo/oai"
    failed_identifiers = set(
        HarvestedPreprint.objects.filter(harvest_status=HarvestStatus.FAILED)
        .values_list("identifier", flat=True)
        .iterator()
    )
    if not failed_identifiers:
        logging.info("Sem preprints com falha para reprocessar.")
        return

    for identifier in failed_identifiers:
        try:
            rec = service_oai_pmh_get_record(
                url=url,
                identifier=identifier,
                verify=verify,
            )
        except Exception as exc:
            preprint = HarvestedPreprint.objects.filter(identifier=identifier).first()
            if preprint:
                exc_context = ExceptionContext(
                    harvest_object=preprint,
                    log_model=HarvestErrorLogPreprint,
                    fk_field="preprint",
                )
                exc_context.add_exception(
                    exception=exc,
                    field_name="get_record",
                    context_data={"identifier": identifier},
                )
                exc_context.save_to_db()
                exc_context.mark_status_harvest()
            logging.warning(
                "Falha ao buscar preprint %s via GetRecord: %s",
                identifier,
                exc,
            )
            continue
        harvest_preprint(recs=[rec], user=user)



@celery_app.task(name="Retry failed books")
def retry_failed_books(username, user_id=None, db_name="scielobooks_1a", headers=None):
    failed_books = HarvestedBooks.objects.filter(
        harvest_status=HarvestStatus.FAILED
    ).values_list("identifier", flat=True)
    if not failed_books:
        logging.info("Sem books com falha para reprocessar.")
        return        
    for identifier in failed_books.iterator():
        harvest_single_book_in_couchdb.delay(
            username=username,
            doc_id=identifier,
            db_name=db_name,
            headers=headers,
        )


@celery_app.task(name="Retry failed SciELO data")
def retry_failed_scielo_data():
    failed_data = HarvestedSciELOData.objects.filter(
        harvest_status=HarvestStatus.FAILED
    )
    if not failed_data:
        logging.info("Sem SciELO Data com falha para reprocessar.")
        return
    for obj in failed_data.iterator():
        harvest_single_scielo_data(harvested_obj=obj)


@celery_app.task(name="Reindex failed preprints")
def reindex_failed_preprints():
    failed = HarvestedPreprint.objects.filter(index_status=IndexStatus.FAILED)
    for obj in failed.iterator():
        index_harvested_instance(instance=obj, index_name=obj.index_name)


@celery_app.task(name="Reindex failed books")
def reindex_failed_books():
    failed = HarvestedBooks.objects.filter(index_status=IndexStatus.FAILED)
    for obj in failed.iterator():
        index_harvested_instance(instance=obj, index_name=obj.index_name)


@celery_app.task(name="Reindex failed SciELO data")
def reindex_failed_scielo_data():
    failed = HarvestedSciELOData.objects.filter(index_status=IndexStatus.FAILED)
    for obj in failed.iterator():
        index_harvested_instance(instance=obj, index_name=obj.index_name)
