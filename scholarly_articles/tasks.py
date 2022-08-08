from django.contrib.auth import get_user_model

from config import celery_app

from scholarly_articles.scripts import unpaywall


def load_unpaywall_row(row):
    """A pointless Celery task to demonstrate usage."""
    task_load_unpaywall_row.apply_async(kwargs={"row": row})


@celery_app.task()
def task_load_unpaywall_row(row):
    """A pointless Celery task to demonstrate usage."""
    unpaywall.load(row)
