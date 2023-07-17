import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from article import models
from config import celery_app
from core.utils import utils as core_utils

logger = logging.getLogger(__name__)

User = get_user_model()


@celery_app.task(name="Load OpenAlex data to SourceArticle")
def load_openalex(user_id, date=2012, country="BR"):
    """
    Retrieves article data from OpenALex API for a specific year and populate the article.models.Article

    Sync or Async
    Param: date is a integer representing the date range in the format 'YYYY'.

    The endpoint OpenAlex: https://api.openalex.org/works/?filter=institutions.country_code:{country},publication_year:{date}&per-page=200&cursor=*"

    The API of OpenALex only allow 200 itens per request.

    Example running this function on python terminal

        from article import tasks

        tasks.load_openalex(date=2012)


    Running using a script: 

    python manage.py runscript load_openalex --script-args 1 2012

    The OpenAlex API format is something like the format below:
      "meta":{
         "count":97151,
         "db_response_time_ms":60,
         "page":null,
         "per_page":100,
         "next_cursor":"IlszODksICdodHRwczovL29wZW5hbGV4Lm9yZy9XMTk2NjA4NDkxNSddIg=="
      },
      "results":[
         {
            "id":"https://openalex.org/W2114538920",
            "doi":"https://doi.org/10.1016/s0140-6736(12)60646-1",
            "title":"Global physical activity levels: surveillance progress, pitfalls, and prospects",
            "display_name":"Global physical activity levels: surveillance progress, pitfalls, and prospects",
            "publication_year":2012,
            "publication_date":"2012-07-01",
            "ids":{
               "openalex":"https://openalex.org/W2114538920",
               "doi":"https://doi.org/10.1016/s0140-6736(12)60646-1",
               "mag":"2114538920",
               "pmid":"https://pubmed.ncbi.nlm.nih.gov/22818937"
            },
            "language":"en",
            "primary_location":{
               "is_oa":false,
               "landing_page_url":"https://doi.org/10.1016/s0140-6736(12)60646-1",
               "pdf_url":null,
               "source":{
                  "id":"https://openalex.org/S49861241",
                  "display_name":"The Lancet",
                  "issn_l":"0140-6736",
                  "issn":[
                     "1474-547X",
                     "0099-5355",
                     "0140-6736"
                  ],
                  "is_oa":false,
                  "is_in_doaj":false,
                  "host_organization":"https://openalex.org/P4310320990",
                  "host_organization_name":"Elsevier BV",
                  "host_organization_lineage":[
                     "https://openalex.org/P4310320990"
                  ],
                  "host_organization_lineage_names":[
                     "Elsevier BV"
                  ],
                  "type":"journal"
               },
               "license":null,
               "version":null
            },
            "type":"journal-article",
            "open_access":{
               "is_oa":true,
               "oa_status":"green",
               "oa_url":"https://api.research-repository.uwa.edu.au/ws/files/79079771/AAM_Global_physical_activity_levels.pdf",
               "any_repository_has_fulltext":true
            },
            "authorships":[
               {
                  "author_position":"first",
                  "author":{
                     "id":"https://openalex.org/A4354288008",
                     "display_name":"Pedro C. Hallal",
                     "orcid":null
                  },
                  "institutions":[
                     {
                        "id":"https://openalex.org/I169248161",
                        "display_name":"Universidade Federal de Pelotas",
                        "ror":"https://ror.org/05msy9z54",
                        "country_code":"BR",
                        "type":"education"
                     }
                  ],
                  "is_corresponding":true,
                  "raw_affiliation_string":"Universidade Federal de Pelotas, Pelotas, Brazil",
                  "raw_affiliation_strings":[
                     "Universidade Federal de Pelotas, Pelotas, Brazil"
                  ]
               },
               {
                  "author_position":"middle",
                  "author":{
                     "id":"https://openalex.org/A4359769260",
                     "display_name":"Lars Bo Andersen",
                     "orcid":null
                  },
                  "institutions":[
                     {
                        "id":"https://openalex.org/I177969490",
                        "display_name":"University of Southern Denmark",
                        "ror":"https://ror.org/03yrrjy16",
                        "country_code":"DK",
                        "type":"education"
                     },
                     {
                        "id":"https://openalex.org/I76283144",
                        "display_name":"Norwegian School of Sport Sciences",
                        "ror":"https://ror.org/045016w83",
                        "country_code":"NO",
                        "type":"education"
                     }
                  ],
                  "is_corresponding":false,
                  "raw_affiliation_string":"Department of Sport Medicine, Norwegian School of Sport Sciences, Oslo, Norway; Department of Exercise Epidemiology, Centre for Research in Childhood Health, University of Southern Denmark, Odense, Denmark",
                  "raw_affiliation_strings":[
                     "Department of Sport Medicine, Norwegian School of Sport Sciences, Oslo, Norway",
                     "Department of Exercise Epidemiology, Centre for Research in Childhood Health, University of Southern Denmark, Odense, Denmark"
                  ]
               }
        } 
    """
    url = (
        settings.URL_API_OPENALEX
        + f"?filter=institutions.country_code:{country},publication_year:{date}&per-page=200&cursor=*"
    )

    _source, _ = models.Source.objects.get_or_create(name="OPENALEX")

    try:
        while True:
            payload = core_utils.fetch_data(url, json=True, timeout=30, verify=True)

            if payload.get("results"):
                for item in payload.get("results"):
                    article = {}
                    article["specific_id"] = item.get("id")
                    article["doi"] = item.get("doi")
                    article["year"] = item.get("publication_year")
                    article["is_paratext"] = item.get("is_paratext")
                    article["updated"] = item.get("updated_date")
                    article["created"] = item.get("created_date")
                    article["source"] = _source
                    article["raw"] = item

                    article, is_created = models.SourceArticle.create_or_update(**article
                                                                                )

                    logger.info(
                        "%s: %s"
                        % (
                            "Created article" if is_created else "Updated article",
                            article,
                        )
                    )

                cursor = payload["meta"]["next_cursor"]

                # Url with new cursor
                url = url.split("cursor=")[0] + "cursor=" + cursor
            else:
                logger.info("No more articles found.")
                return
    except Exception as e:
        logger.info(f"Unexpected error: {e}")


@celery_app.task(name="Load OpenAlex to Article models")
def load_openalex_article(user_id, update=True):
    """
    This task read the article.models.SourceArticle
    and add the articles to article.models.Article

    Only associaded the official institutions when exists and if from MEC.

    Param update: If update == True all articles will be update otherwise just the article will created.

    """

    user = User.objects.get(id=user_id)

    def affiliation(aff_string):
        name = aff_string

        aff_obj, _ = models.Affiliation.create_or_update(
            **{"name": name}
        )

        return aff_obj

    def contributors(authors):
        """
        TODO: Nesse momento tem autores duplicados no futuro corrigir
        """
        contributors = []

        for au in authors:
            # if exists author
            if au.get("author"):
                display_name = au.get("author").get("display_name")

                if display_name:
                    family = (
                        " ".join(display_name.split(" ")[1:]).strip()
                        if display_name
                        else ""
                    )
                    given = display_name.split(" ")[0].strip() if display_name else ""

                    author_dict = {
                        "family": family,
                        "given": given,
                        "orcid": au.get("author").get("orcid"),
                    }

                    # If exists institutions
                    if au.get("raw_affiliation_strings"):
                        author_dict.update(
                            {"affiliation": affiliation("|".join(au.get("raw_affiliation_strings")))}
                        )

                    contributor, _ = models.Contributor.create_or_update(
                        **author_dict
                    )

                    contributors.append(contributor)

        return contributors

    # read SourceArticle
    for article in models.SourceArticle.objects.filter(source__name="OPENALEX").iterator():
        try:

            doi = article.doi
            # title
            title = core_utils.nestget(article.raw, "title")
            
            if not update:
                if doi:
                    if models.Article.objects.filter(doi=doi).exists():
                        continue

                if title:
                    if models.Article.objects.filter(title=title).exists():
                        continue

            # Number
            number = core_utils.nestget(article.raw, "biblio", "issue")
            # Volume
            volume = core_utils.nestget(article.raw, "biblio", "volume")
            # Year
            year = core_utils.nestget(article.raw, "publication_year")

            # Get the journal data
            if article.raw.get("primary_location"):
                journal_data = core_utils.nestget(article.raw, "primary_location", "source")
                if journal_data:
                    j_issn_l = journal_data.get("issn_l")
                    if journal_data.get("issn"):
                        j_issns = ",".join(journal_data.get("issn"))
                    j_name = journal_data.get("display_name")
                    j_is_in_doaj = journal_data.get("is_in_doaj")

                journal, _ = models.Journal.create_or_update(
                    **{
                        "journal_issn_l": j_issn_l,
                        "journal_issns": j_issns,
                        "journal_name": j_name,
                        "journal_is_in_doaj": j_is_in_doaj,
                    },
                )
            else:
                journal = None

            # APC
            is_apc = (
                "YES" if bool(core_utils.nestget(article.raw, "apc_list")) else "NO"
            )

            # Open Access Status
            oa_status = core_utils.nestget(article.raw, "open_access", "oa_status")

            # license
            if article.raw.get("primary_location"):
                if core_utils.nestget(article.raw, "primary_location", "license"):
                    license, _ = models.License.create_or_update(
                        **{
                            "name": core_utils.nestget(
                                article.raw, "primary_location", "license"
                            )
                        }
                    )
                else:
                    license = None

            article_dict = {
                "doi": doi,
                "title": title,
                "number": number,
                "volume": volume,
                "year": year,
                "is_ao": core_utils.nestget(article.raw, "open_access", "is_ao"),
                "sources": [models.Source.objects.get(name="OPENALEX")],
                "journal": journal,
                "apc": is_apc,
                "open_access_status": oa_status,
                "contributors": contributors(
                    core_utils.nestget(article.raw, "authorships")
                ),
                "license": license,
            }

            article, created = models.Article.create_or_update(**article_dict)

            logger.info("Article: %s, %s" % (article, created))
        except Exception as e:
            logger.error("Erro on save article: %s" % e)
