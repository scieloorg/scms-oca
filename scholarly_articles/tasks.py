import json

from config import celery_app
from scholarly_articles.unpaywall import unpaywall
from scholarly_articles.unpaywall import load_data


@celery_app.task()
def load_unpaywall_row(row):
    """
    Load each row of unpaywall data.

    Sync or Async function

    Param row: JSON
    """
    unpaywall.load(row)


@celery_app.task()
def load_unpaywall(file_path):
    """
    Load the data from unpaywall file.

    Sync or Async function

    Param file_path: String with the path of the JSON like file.
    """
    with open(file_path) as fp:
        for row in fp.readlines():
            load_unpaywall_row(json.loads(row))


@celery_app.task()
def load_journal_articles(from_year=1900, resource_type='journal-article'):
    """
    Load the data from unpaywall model to ScholarlyArticles.

    Sync or Async function
    """
    load_data.load(from_year, resource_type)
