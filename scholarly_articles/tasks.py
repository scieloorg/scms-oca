import gzip

from django.contrib.auth import get_user_model

from config import celery_app
from scholarly_articles.unpaywall import load_data, unpaywall

User = get_user_model()

@celery_app.task()
def load_unpaywall(file_path, user_id):
    """
    Load the data from unpaywall file.

    Sync or Async function

    Param file_path: String with the path of the JSON like file compressed or not.
    """
    user = User.objects.get(id=user_id)

    try:
        with gzip.open(file_path, "rb") as f:
            for line, row in enumerate(f):
                unpaywall.load(line, row, user)
    except OSError:
        with open(file_path, "rb") as f:
            for line, row in enumerate(f):
                unpaywall.load(line, row, user)


@celery_app.task()
def load_journal_articles(from_year=1900, resource_type='journal-article'):
    """
    Load the data from unpaywall model to ScholarlyArticles.

    Sync or Async function
    """
    load_data.load(from_year, resource_type)
