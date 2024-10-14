import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from journal import models
from config import celery_app
from core.models import Source
from core.utils import utils as core_utils

logger = logging.getLogger(__name__)

User = get_user_model()


@celery_app.task(name="Load OpenAlex data to SourceJournal")
def load_journal_openalex(user_id, country="BR", length=None):
    """
    Retrieves journal data from OpenALex API for a specific year and populate the journal.models.SourceJournal

    Sync or Async

    Args:
        length: A integer that determine the quantity of item to be get from OpenAlex.
        country: A string represent the code of country to be get from OpenAlex.

    The endpoint OpenAlex: https://api.openalex.org/sources/?filter=country_code:{country}&per-page=200&cursor=*"

    The API of OpenALex only allow 200 itens per request.

    Example running this function on python terminal

        from journal import tasks

        tasks.load_journal_openalex(country=br)

    Running using a script:

    python manage.py runscript load_journal_openalex --script-args 1 BR

    The OpenAlex API format is something like the format below:
      {
        "meta": {
          "count": 1,
          "db_response_time_ms": 24,
          "page": 1,
          "per_page": 25,
          "groups_count": null
        },
        "results": [
          {
            "id": "https://openalex.org/S183843087",
            "issn_l": "0100-879X",
            "issn": [
              "0100-879X",
              "1414-431X"
            ],
            "display_name": "Brazilian Journal of Medical and Biological Research",
            "host_organization": "https://openalex.org/P4310311980",
            "host_organization_name": "Associação Brasileira de Divulgação Científica",
            "host_organization_lineage": [
              "https://openalex.org/P4310311980"
            ],
            "works_count": 5059,
            "cited_by_count": 123202,
            "summary_stats": {
              "2yr_mean_citedness": 1.8280254777070064,
              "h_index": 120,
              "i10_index": 3769
            },
            "is_oa": true,
            "is_in_doaj": true,
            "is_core": true,
            "ids": {
              "openalex": "https://openalex.org/S183843087",
              "issn_l": "0100-879X",
              "issn": [
                "0100-879X",
                "1414-431X"
              ],
              "mag": "183843087",
              "wikidata": "https://www.wikidata.org/entity/Q2025772"
            },
            "homepage_url": "http://www.scielo.br/bjmbr",
            "apc_prices": [
              {
                "price": 3300,
                "currency": "BRL"
              },
              {
                "price": 1600,
                "currency": "USD"
              }
            ],
            "apc_usd": 1600,
            "country_code": "BR",
            "societies": [
              
            ],
            "alternate_titles": [
              
            ],
            "abbreviated_title": null,
            "type": "journal",
            "counts_by_year": [
              {
                "year": 2024,
                "works_count": 94,
                "cited_by_count": 4798
              },
              {
                "year": 2023,
                "works_count": 113,
                "cited_by_count": 7241
              },
              {
                "year": 2022,
                "works_count": 106,
                "cited_by_count": 8060
              },
              {
                "year": 2021,
                "works_count": 162,
                "cited_by_count": 8454
              },
              {
                "year": 2020,
                "works_count": 164,
                "cited_by_count": 7956
              },
              {
                "year": 2019,
                "works_count": 144,
                "cited_by_count": 6941
              },
              {
                "year": 2018,
                "works_count": 174,
                "cited_by_count": 6333
              },
              {
                "year": 2017,
                "works_count": 191,
                "cited_by_count": 6058
              },
              {
                "year": 2016,
                "works_count": 151,
                "cited_by_count": 5893
              },
              {
                "year": 2015,
                "works_count": 132,
                "cited_by_count": 6025
              },
              {
                "year": 2014,
                "works_count": 167,
                "cited_by_count": 6158
              },
              {
                "year": 2013,
                "works_count": 168,
                "cited_by_count": 6121
              },
              {
                "year": 2012,
                "works_count": 184,
                "cited_by_count": 6001
              }
            ],
            "works_api_url": "https://api.openalex.org/works?filter=primary_location.source.id:S183843087",
            "updated_date": "2024-10-10T08:55:30.960651",
            "created_date": "2016-06-24"
          }
        ]
      }
    
    
    """
    url = (
        settings.URL_API_OPENALEX_JOURNALS
        + f"?filter=country_code:{country}&per-page=200&cursor=*"
    )

    _source, _ = Source.objects.get_or_create(name="OPENALEX")

    try:
        flag = True
        journal_count = 0

        while flag:
            payload = core_utils.fetch_data(url, json=True, timeout=30, verify=True)

            if payload.get("results"):
                for item in payload.get("results"):
                    journal = {}
                    journal["specific_id"] = item.get("id")
                    journal["issns"] = "|".join(item.get("issn")) if isinstance(item.get("issn"), list) else item.get("issn")
                    journal["issn_l"] = item.get("issn_l")
                    journal["country_code"] = item.get("country_code")
                    journal["title"] = item.get("display_name")
                    journal["updated"] = item.get("updated_date")
                    journal["created"] = item.get("created_date")
                    journal["source"] = _source
                    journal["raw"] = item

                    journal, created = models.SourceJournal.create_or_update(**journal)

                    logger.info(
                        "%s: %s"
                        % (
                            "Created journal" if created else "Updated journal",
                            journal,
                        )
                    )
                    journal_count += 1

                cursor = payload["meta"]["next_cursor"]

                # Url with new cursor
                url = url.split("cursor=")[0] + "cursor=" + cursor

                if length and (length <= journal_count):
                    flag = False

            else:
                logger.info("No more journals found.")
                return
    except Exception as e:
        logger.info(f"Unexpected error: {e}")
