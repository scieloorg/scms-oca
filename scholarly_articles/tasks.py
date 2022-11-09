import gzip

from django.contrib.auth import get_user_model

from config import celery_app
from scholarly_articles.unpaywall import load_data, unpaywall, supplementary
from scholarly_articles import models as article_models
from institution import models as institution_models

User = get_user_model()


@celery_app.task()
def load_unpaywall(user_id, file_path):
    """
    Load the data from unpaywall file.

    Sync or Async function

    Param file_path: String with the path of the JSON like file compressed or not.
    Param user: The user id passed by kwargs on tasks.kwargs
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
def load_journal_articles(user_id, from_year=1900, resource_type='journal-article', is_paratext=False):
    """
    Load the data from unpaywall model to ScholarlyArticles.

    Sync or Async function

    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    load_data.load(from_year, resource_type, is_paratext, user)


@celery_app.task()
def load_supplementary(user_id, file_path):
    """
    Load the data from supplementary file.

    Sync or Async function

    Param file_path: String with the path of the CSV file.
    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    try:
        with gzip.open(file_path, "rb") as f:
            for line, row in enumerate(f):
                supplementary.load(line, row, user)
    except OSError:
        with open(file_path, "rb") as f:
            for line, row in enumerate(f):
                supplementary.load(line, row, user)


@celery_app.task(bind=True, name="Set official institution to affiliation")
def set_official(self):
    """
    Correlates declared institution name with official institution name.

    Sync or Async function
    """
    for institution in institution_models.Institution.objects.filter(source='MEC').iterator():
        for aff in article_models.Affiliations.objects.filter(
                official__isnull=True,
                name__icontains=institution.name).iterator():
            aff.official = institution
            aff.save()
