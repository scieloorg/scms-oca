import gzip
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app
from core.utils import utils as core_utils
from scholarly_articles import models, utils
from scholarly_articles.crossref import crossref
from scholarly_articles.unpaywall import (
    affiliation,
    load_data,
    supplementary,
    unpaywall,
)

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
def load_crossref(user_id, from_update_date=2012, until_update_date=2012):
    """
    Retrieves article data from CrossRef API for a given range of years.

    Sync or Async
    Param: from_update_date and until_update_date are strings representing the date range in the format 'YYYY'.

    Example running this function on python terminal

        from scholarly_articles import tasks
        from scholarly_articles import models

        tasks.load_crossref(from_update_date=2022, until_update_date=2023)


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
    url = (
        settings.URL_API_CROSSREF
        + f"?query.affiliation=Brazil&filter=type:journal-article,from-update-date:{from_update_date},until-update-date:{until_update_date}&mailto=atta.jamil@gmail.com&cursor=*"
    )

    dados = [
        "publisher",
        "DOI",
        "type",
        "source",
        "title",
        "volume",
        "author",
        "container-title",
        "issued",
        "issue",
        "license",
        "ISSN",
    ]

    try:
        while True:

            data = core_utils.fetch_data(url, json=True, timeout=30, verify=True)
            articles = []
            if data["status"] == "ok":
                for item in data["message"]["items"]:
                    article_dict = {field: item.get(field, "") for field in dados}
                    articles.append(article_dict)

                # If there were no more items, the interaction stops
                if not data["message"]["items"]:
                    return "No more articles found."

                # Send articles to a function that will save in the database
                crossref.load(articles)

                cursor = data["message"]["next-cursor"]
                # Url with new cursor
                url = url.split("cursor=")[0] + "cursor=" + cursor

    except Exception as e:
        logger.info(f"Unexpected error: {e}")


@celery_app.task(name=_("Sanitize by journals"))
def sanitize_journals(user_id, journals_ids):
    """
    This task receive a list of journals and check if has duplicate. 
    Cast the more complete journal to be reassigns to the articles.
    """
    
    for id in journals_ids:
        journal = models.Journals.objects.get(pk=id)
        journals = utils.check_duplicate_journal(journal)

        if journals:
            logger.info(
                "Duplicate journals %s, size: %s" % (journals, len(journals))
            )

            cast_journal = None

            for j in journals:
                if (
                    j.journal_issn_l
                    and j.journal_issns
                    and j.journal_name
                    and j.publisher
                ):
                    if len(j.journal_issns) > 9:
                        cast_journal = j
                        break
                    elif len(j.journal_issns) == 9:
                        cast_journal = j
                        break
                if j.journal_issn_l and j.journal_issns and j.journal_name:
                    if len(j.journal_issns) > 9:
                        cast_journal = j
                        break
                    elif len(j.journal_issns) == 9:
                        cast_journal = j
                        break
                if j.journal_issn_l and j.journal_issns:
                    if len(j.journal_issns) > 9:
                        cast_journal = j
                        break
                    elif len(j.journal_issns) == 9:
                        cast_journal = j
                        break
                if j.journal_issn_l and j.journal_name:
                    cast_journal = j
                    continue
                if j.journal_issns and j.journal_name:
                    if len(j.journal_issns) > 9:
                        cast_journal = j
                        break
                    elif len(j.journal_issns) == 9:
                        cast_journal = j
                        break
                if j.journal_issn_l or j.journal_issns or j.journal_name:
                    cast_journal = j

            logger.info("Casted journal: %s" % cast_journal)

            logger.info("Reassigned articles: %s" % utils.reassignment_articles(cast_journal, journals))


@celery_app.task(name=_("Sanitize all Journals"))
def sanitize_all_journals(user_id, loop_size=1000):
    """
    This task go to all journals and check if has duplicate. 

    If has the article are reassign to more complete journal.   

    After this task problably will be orphans journals.

    This function get the size of journal divide per loop_size and raise 
    a list of task based on this division.

    So if we have 1000 journal it will be raise a 1 task to sanitize this journals 
    So if we have 2000 journal it will be raise a 2 task to sanitize this journals 

    This way we raise ``Journals.count`` divided by loop_size task to do the work.
    """
    count = 0
    journals = models.Journals.objects.all()
    total = journals.count()
    offset = loop_size

    for i in range(int(journals.count() / loop_size) + 1):
        _journals = journals[count:offset]
        sanitize_journals.apply_async(
            kwargs={"user_id": user_id, "journals_ids": [journal.id for journal in _journals]}
        )
        count += loop_size
        offset += loop_size

        if offset > total:
            offset = total


@celery_app.task(name=_("Remove journals without articles associated"))
def remove_orphans_journals(user_id):
    """
    This task remove all journals with no associated articles.
    """
    logger.info("Checking the journals....")
    
    journals = utils.check_articles_journals()

    removed = [journal.delete() for journal in journals]

    logger.info("Reassigned articles: %s" % removed)