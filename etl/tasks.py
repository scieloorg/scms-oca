from django.conf import settings

from config import celery_app
from etl.services import process_pending_items


@celery_app.task(name="[ETL] Process pending silver items")
def process_pending_silver_etl(limit=None, user_id=None, document_type=None):
    """
    Processes one batch of pending ETL items.

    Scheduling is handled by Celery Beat — this task does NOT re-enqueue itself.
    Configure the run interval in the Wagtail admin under Celery > Periodic Tasks.
    """
    if limit is None:
        limit = settings.ETL_DEFAULT_BATCH_SIZE
    return process_pending_items(limit=limit, document_type=document_type)


@celery_app.task(name="[ETL] Retry failed silver ETL items")
def retry_failed_silver_etl(limit=None, user_id=None):
    """
    Retries one batch of failed ETL items.

    Scheduling is handled by Celery Beat — this task does NOT re-enqueue itself.
    Configure the run interval in the Wagtail admin under Celery > Periodic Tasks.
    """
    if limit is None:
        limit = settings.ETL_DEFAULT_BATCH_SIZE
    return process_pending_items(limit=limit, retry_failed=True)
