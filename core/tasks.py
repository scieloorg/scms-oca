from config import celery_app

from core import controller


@celery_app.task()
def check_values():
    """
    Check for missing values.
    Sync or Async function
    """

    controller.check_values()
