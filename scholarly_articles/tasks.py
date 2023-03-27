import gzip


from django.contrib.auth import get_user_model

from config import celery_app
from scholarly_articles.unpaywall import (
    load_data,
    unpaywall,
    supplementary,
    affiliation,
)
from scholarly_articles.crossref import (
    crossref,
    fetch_data_retry,
    
)

import logging


logger = logging.getLogger(__name__)


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
def load_journal_articles(
    user_id, from_year=1900, resource_type="journal-article", is_paratext=False
):
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


@celery_app.task(bind=True, name="Set official institution or country to affiliation")
def complete_affiliation_data(self):
    """
    Correlates declared institution name with official institution name.

    Sync or Async function
    """
    return affiliation.complete_affiliation_data()


@celery_app.task()
def load_crossref(from_update_date, until_update_date):
    """
    Retrieves article data from CrossRef API for a given range of years.

    Sync or Async
    Param: from_update_date and until_update_date are strings representing the date range in the format 'YYYY'.
    """
    url = f'https://api.crossref.org/works?query.affiliation=Brazil&filter=type:journal-article,from-update-date:{from_update_date},until-update-date:{until_update_date}&mailto=samuelveiga710@gmail.com&cursor=*'
    
    dados = ['DOI', 'title', 'volume', 'publisher', 'source', 'type',]

    try:
        while True:

            data = fetch_data_retry.request_retry(url)
            articles = []
            
            if data['status'] == 'ok':
                for item in data['message']['items']:
                    article_dict = {field: item.get(field, '') for field in dados}
                    articles.append(article_dict)

                if not data['message']['items']:
                    return "No articles found."

                # Send articles to a function that will save in the database
                crossref.load(articles)

                cursor = data['message']['next-cursor']
                url = url[:168] + cursor

    except Exception as e:
        logger.info(f'Error: {e}')

   
