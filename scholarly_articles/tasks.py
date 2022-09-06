import orjson
import gzip

from config import celery_app
from scholarly_articles.unpaywall import unpaywall
from scholarly_articles.unpaywall import load_data


@celery_app.task()
def load_unpaywall(file_path):
    """
    Load the data from unpaywall file.

    Sync or Async function

    Param file_path: String with the path of the JSON like file compressed or not.
    """
    try:
        with gzip.open(file_path, "rb") as f:
            for line, row in enumerate(f):
                row = orjson.loads(row)
                print("Line: %s, id: %s" % (line+1, row['doi']))
                unpaywall.load(row)
    except OSError:
        with open(file_path, "rb") as f:
            for line, row in enumerate(f):
                row = orjson.loads(row)
                print("Line: %s, id: %s" % (line+1, row['doi']))
                unpaywall.load(row)


@celery_app.task()
def load_journal_articles(from_year=1900, resource_type='journal-article'):
    """
    Load the data from unpaywall model to ScholarlyArticles.

    Sync or Async function
    """
    load_data.load(from_year, resource_type)
