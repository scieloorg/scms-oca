import gzip
import json
import logging
import re

import django
import pandas as pd
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext as _

from config import celery_app
from core.utils import utils
from scholarly_articles import models
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
def load_crossref(from_update_date=2012, until_update_date=2012):
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
            "ied": {
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
            data = utils.fetch_data(url, json=True, timeout=30, verify=True)
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


@celery_app.task(name=_("Load sucupira data"))
def load_sucupira(file_path, user_id):
    """
    Load the data from sucupira file.

    Sync or Async function

    Param file_path: String with the path of the .csv file.
    Param user: The user id passed by kwargs on tasks.kwargs

    Fields used on this load: 
    
        doi = DS_DOI
        id_int_production
        title = NM_PRODUCAO
        volume = NR_VOLUME
        number = NR_SERIE
        year = AN_BASE_PRODUCAO
        open_access_status = NA
        use_license = CC-By
        license = https://opendefinition.org/licenses/cc-by/
        apc = NA
        contributors = DICT_AUTORES
        journal = DS_ISSN (refe to journal)
        source = SUCUPIRA

    """

    def get_institution(institution_acron):
        """
        Get the institution from models.Institution.

        Example of the acronym of institution:

            UFPA - ABAETETUBA
            UFPB/AREIA
            UNESP-ARAR
            UTFPR-MD
            CCD/SES
            CEFET/MG
        """

        # makes a treatment to obtain the institution
        institution_acron = institution_acron.split("/")[0]
        institution_acron = institution_acron.split(" / ")[0]
        institution_acron = institution_acron.split("-")[0]
        institution_acron = institution_acron.split(" - ")[0]
        institution_acron = institution_acron.strip()

        if models.Institution.objects.filter(acronym=institution_acron).exists():
            return models.Institution.objects.filter(acronym=institution_acron)[0]

    def get_journal(journal_issn, journal_name):
        """
        This method try to get the journal on database if exists and create otherwise.
        """
        journals = models.Journals.objects.filter(
            Q(journal_issn_l=journal_issn) | Q(journal_issns=journal_issn)
        )

        try:
            journal = journals[0]
        except IndexError:
            journal = models.Journals()
            journal.journal_issns = journal_issn
            journal.journal_name = journal_name
            journal.save()

        return journal

    def get_license(url, name=None):
        """
        This method try to get the license on database if exists and create otherwise.
        """
        license, created = models.License.objects.get_or_create(
            **{"name": name, "url": url}
        )
        return license

    user = User.objects.get(id=user_id)

    df = pd.read_csv(file_path)

    for index, row in df.iterrows():
        try:
            article_dict = {
                "doi": "" if str(row["DS_DOI"]) == "nan" else row["DS_DOI"],
                "id_int_production": str(row["ID_ADD_PRODUCAO_INTELECTUAL"]),
                "title": row["NM_PRODUCAO"][0:255],
                "number": row["NR_SERIE"],
                "volume": row["NR_VOLUME"],
                "year": row["AN_BASE_PRODUCAO"],
                "source": "SUCUPIRA",
                "year": row["AN_BASE_PRODUCAO"],
                "license": get_license("https://opendefinition.org/licenses/cc-by/"),
                "use_license": "CC-BY",
            }
            
            split_ds_issn = row["DS_ISSN"].split(" ")

            issn = re.search("[\S]{4}\-[\S]{4}", split_ds_issn[0]).group()

            journal_name = " ".join(split_ds_issn[1:])
        
            article, created = models.ScholarlyArticles.objects.get_or_create(
                **article_dict
            )

            authors_json = json.loads(row["DICT_AUTORES"])

            for au in authors_json:

                filter_dict = {
                    "family": au["NM_ABNT_AUTOR"].split(",")[0].strip()
                    if "," in au["NM_ABNT_AUTOR"]
                    else au["NM_ABNT_AUTOR"],
                    "given": au["NM_ABNT_AUTOR"].split(",")[1].strip()
                    if "," in au["NM_ABNT_AUTOR"]
                    else au["NM_ABNT_AUTOR"],
                }

                try:
                    contributor, created = models.Contributors.objects.get_or_create(**filter_dict)
                except models.Contributors.MultipleObjectsReturned:
                    contributor = models.Contributors.objects.filter(**filter_dict)[0]

                institution = get_institution(row["SG_ENTIDADE_ENSINO"])
                program, created = models.Programs.objects.get_or_create(
                    **{"name": row["NM_PROGRAMA_IES"], "institution": institution}
                )

                contributor.programs.add(program)
                article.contributors.add(contributor)
                article.journal = get_journal(issn, journal_name)
                article.save()

            logger.info("####%s####, %s" % (index.numerator, article.data))

        except django.db.utils.DataError as e:
            try:
                logger.error("Erro: %s" % (e))
                error = models.ErrorLog()
                error.error_type = str(type(e))
                error.error_message = str(e)[:255]
                error.error_description = (
                    "Erro on processing the Sucupira to ScholarlyArticles."
                )
                error.data_reference = "id:%s" % str(
                    row["ID_ADD_PRODUCAO_INTELECTUAL"]
                ) or str(row["DS_DOI"])
                error.data = article_dict
                error.data_type = "Sucupira"
                error.creator = user
                error.save()
            except Exception as erro:
                logger.error("Erro when saving erro on ErrorLog: %s " % erro)
