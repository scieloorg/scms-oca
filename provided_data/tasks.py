from django.contrib.auth import get_user_model

from config import celery_app

from .controller import load_raw_data, load_article, load_conference, load_thesis
from .models import RawArticle


User = get_user_model()


@celery_app.task()
def load_data_raw(file_path):
    """
    Load the data from provided data files.

    Sync or Async function

    Param file_path: String with the path of the JSON file.
    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=1)

    with open(file_path, "rb") as f:
        for row in f:
            load_raw_data(row, user)


@celery_app.task()
def load_data():
    """
    Load the data from RawArticle model.

    Sync or Async function

    Param file_path: String with the path of the JSON file.
    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=1)

    for record in RawArticle.objects.all().iterator():
        if record.document_type == 'journal article':
            load_article(user, record)
        if record.document_type == 'conference proceedings':
            load_conference(user, record)
        if record.document_type == 'master thesis' or record.document_type == 'doctoral thesis':
            load_thesis(user, record)
