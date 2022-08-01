from django.contrib.auth import get_user_model

from config import celery_app

from scholarly_articles.scripts import load_raw_unpaywall


def load_unpaywall_row(row):
    """A pointless Celery task to demonstrate usage."""
    task_load_unpaywall_row.apply_async(row)


@celery_app.task()
def task_load_unpaywall_row(row):
    """A pointless Celery task to demonstrate usage."""
    load_raw_unpaywall.load(row)
