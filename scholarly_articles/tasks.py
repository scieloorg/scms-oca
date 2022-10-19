import gzip

from django.contrib.auth import get_user_model

from config import celery_app
from scholarly_articles.loads import load_data_raw, load_data


User = get_user_model()

@celery_app.task()
def load_data_raw_json(user_id, file_path, file_source='Unpaywall'):
    """
    Load the data from loads file.

    Sync or Async function

    Param file_path: String with the path of the JSON like file compressed or not.
    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    try:
        with gzip.open(file_path, "rb") as f:
            for line, row in enumerate(f):
                load_data_raw.load(line, row, user, file_source)
    except OSError:
        with open(file_path, "rb") as f:
            for line, row in enumerate(f):
                load_data_raw.load(line, row, user, file_source)


@celery_app.task()
def load_articles_data(from_year, user_id):
    """
    Load the data from loads file.

    Sync or Async function

    Param file_path: String with the path of the JSON like file compressed or not.
    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    load_data.load(from_year=from_year, user=user)
