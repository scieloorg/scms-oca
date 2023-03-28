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
from config.settings.base import (
    URL_API_CROSSREF,
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
    
    The crossref API format is something like the format below:
    
    "status": "ok",
    "message-type": "work-list",
    "message-version": "1.0.0",
    "message": {
        "facets": {
            
        },
        "next-cursor": "DnF1ZXJ5VGhlbkZldGNoBgAAAAAKerflFjFGV1lXWE94VGU2bUMzaVRjNzc2aFEAAAAAIGt0aRZHblpDbkEzT1FvRy0tOGFOZ05EOHVnAAAAACBrdGgWR25aQ25
            BM09Rb0ctLThhTmdORDh1ZwAAAAAZqMEuFk5qWk1fWm1iUVV1V3Nwd3MxN3FqQ3cAAAAAFV5fOBZfNEZlTDBRZ1FuLWZ4NVhlZU9MYzN3AAAAABWPAdcWaDRJMjhrcXVUOGE3dDI1VDhnWHMyZw==",
        "total-results": 37342,
        "items": [
            {
            "indexed": {
                "date-parts": [[2022,4,5]],
                "date-time": "2022-04-05T02:58:23Z",
                "timestamp": 1649127503838
            },
            "reference-count": 0,
            "publisher": "FapUNIFESP (SciELO)",
            "issue": "4",
            "content-domain": {
                "domain": [],
                "crossmark-restriction": false
            },
            "short-container-title": [
                "Rev. IBRACON Estrut. Mater."
            ],
            "published-print": {
                "date-parts": [[2017,8]]
            },
            "DOI": "10.1590/s1983-41952017000400001",
            "type": "journal-article",
            "created": {
                "date-parts": [[2017,8,31]],
                "date-time": "2017-08-31T17:37:46Z",
                "timestamp": 1504201066000
            },
            "page": "787-787",
            "source": "Crossref",
            "is-referenced-by-count": 0,
            "title": [
                "Editorial"
            ],
            "prefix": "10.1590",
            "volume": "10",
            "author": [
                {
                "given": "Américo",
                "family": "Campos Filho",
                "sequence": "first",
                "affiliation": [
                    {
                    "name": ",  Brazil"
                    }
                ]
                },
            ],
            "member": "530",
            "container-title": [
                "Revista IBRACON de Estruturas e Materiais"
            ],
        ]
    }
    """
    url = URL_API_CROSSREF + f'?query.affiliation=Brazil&filter=type:journal-article,from-update-date:{from_update_date},until-update-date:{until_update_date}&cursor=*'
    
    dados = [
        'publisher', 
        'DOI', 
        'type', 
        'source', 
        'title', 
        'volume', 
        'author', 
        'container-title'
    ]

    try:
        while True:

            data = fetch_data_retry.request_retry(url, total=10, backoff_factor=1)
            articles = []
            if data['status'] == 'ok':
                for item in data['message']['items']:
                    article_dict = {field: item.get(field, '') for field in dados}
                    articles.append(article_dict)

                # If there were no more items, the interaction stops
                if not data['message']['items']:
                    return "No more articles found."

                # Send articles to a function that will save in the database
                crossref.load(articles)

                cursor = data['message']['next-cursor']
                # Url with new cursor
                url = url.split('cursor=')[0] + 'cursor=' + cursor

    except Exception as e:
        logger.info(f'Error: {e}')

   
