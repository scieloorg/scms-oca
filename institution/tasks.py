import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from institution import models
from core.models import Source
from config import celery_app
from core.utils import utils as core_utils

from institution.models import Institution, SourceInstitution, InstitutionTranslateName

logger = logging.getLogger(__name__)

User = get_user_model()


@celery_app.task(name="Load OpenAlex Institution data to SourceInstitution")
def load_institution(user_id, length=None, country=None):
    """
    Retrieves institution data from OpenALex API for a specific year and populate the instituion.models.SourceInstitution

    Sync or Async

    The endpoint OpenAlex: https://api.openalex.org/institutions?per-page=200&cursor=* or https://api.openalex.org/institutions?filter=country_code:br&per-page=200&cursor=*

    The API of OpenALex only allow 200 itens per request.

    Example running this function on python terminal

        from instituion import tasks

        tasks.load_institution(length=2000, country="BR")


    Running using a script:

    python manage.py runscript load_openalex --script-args 1 2000 BR

    The OpenAlex API format is something like the format below:

        "meta": {
            "count": 1733,
            "db_response_time_ms": 91,
            "page": null,
            "per_page": 200,
            "next_cursor": "IlsyOTkxLCAnaHR0cHM6Ly9vcGVuYWxleC5vcmcvSTQyMTAxMjg2MDQnXSI="
        },
        "results": [
            {
            "id": "https://openalex.org/I17974374",
            "ror": "https://ror.org/036rp1748",
            "display_name": "Universidade de São Paulo",
            "country_code": "BR",
            "type": "education",
            "homepage_url": "http://www5.usp.br/en/",
            "image_url": "https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/Webysther%2020160310%20-%20Logo%20USP.svg",
            "image_thumbnail_url": "https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/Webysther%2020160310%20-%20Logo%20USP.svg&width=300",
            "display_name_acronyms": [
                "USP"
            ],
            "display_name_alternatives": [

            ],
            "repositories": [

            ],
            "works_count": 309714,
            "cited_by_count": 4385451,
            "summary_stats": {
                "2yr_mean_citedness": 2.5257123668809363,
                "h_index": 444,
                "i10_index": 96684
            },
            "ids": {
                "openalex": "https://openalex.org/I17974374",
                "ror": "https://ror.org/036rp1748",
                "mag": "17974374",
                "grid": "grid.11899.38",
                "wikipedia": "https://en.wikipedia.org/wiki/University%20of%20Su00e3o%20Paulo",
                "wikidata": "https://www.wikidata.org/wiki/Q835960"
            },
            "geo": {
                "city": "São Paulo",
                "geonames_city_id": "3448439",
                "region": null,
                "country_code": "BR",
                "country": "Brazil",
                "latitude": -23.563051,
                "longitude": -46.730103
            },
            "international": {
                "display_name": {
                "an": "Universidade de São Paulo",
                "ang": "Universidade de São Paulo",
                "ar": "جامعة ساو باولو",
                "arz": "جامعة ساو باولو",
                "ast": "Universidá de São Paulo",
                "az": "San-Paulu Universiteti",
                "be": "Універсітэт Сан-Паўлу",
                "be-tarask": "унівэрсытэт Сан-Паўлу",
                "bg": "Университет на Сау Паулу",
                "bn": "সাও পাওলো বিশ্ববিদ্যালয়",
                "ca": "Universitat de São Paulo",
                "co": "Universidade de São Paulo",
                "cs": "Univerzita São Paulo",
                "cy": "Universidad de São Paulo",
                "da": "Universidade de São Paulo",
                "de": "Universidade de São Paulo",
                "el": "Πανεπιστήμιο του Σάο Πάολο",
                "en": "University of São Paulo",
                "eo": "Universitato de San-Paŭlo",
                "es": "Universidad de São Paulo",
                "et": "São Paulo ülikool",
                "eu": "São Pauloko Unibertsitatea",
                "fa": "دانشگاه سائو پائولو",
                "fi": "São Paulon yliopisto",
                "fr": "université de São Paulo",
                "gl": "Universidade de São Paulo",
                "gsw": "Universidade de São Paulo",
                "he": "אוניברסיטת סאו פאולו",
                "hu": "São Pauló-i Egyetem",
                "hy": "Սան Պաուլուի համալսարան",
                "id": "Universitas São Paulo",
                "it": "Universidade de São Paulo",
                "ja": "サンパウロ大学",
                "kk": "Сан-Паулу университеті",
                "ko": "상파울루 대학교",
                "lb": "Universitéit vu São Paulo",
                "lt": "San Paulo universitetas",
                "mt": "Università ta’ São Paulo",
                "nb": "Universidade de São Paulo",
                "nl": "Universiteit van São Paulo",
                "pl": "Uniwersytet São Paulo",
                "pt": "Universidade de São Paulo",
                "pt-br": "Universidade de São Paulo",
                "ru": "Университет Сан-Паулу",
                "sh": "Univerzitet u Sao Paulu",
                "sr": "Универзитет у Сао Паулу",
                "sv": "universitetet i São Paulo",
                "tl": "Unibersidad ng São Paulo",
                "tr": "São Paulo Üniversitesi",
                "uk": "Університет Сан-Паулу",
                "zh": "圣保罗大学",
                "zh-cn": "圣保罗大学",
                "zh-hans": "圣保罗大学",
                "zh-hant": "聖保羅大學",
                "zh-hk": "聖保羅大學"
                }
            },
            "associated_institutions": [
                {
                "id": "https://openalex.org/I4210156537",
                "ror": "https://ror.org/04n6fhj26",
                "display_name": "Clinics Hospital of Ribeirão Preto",
                "country_code": "BR",
                "type": "healthcare",
                "relationship": "related"
                },
                {
                "id": "https://openalex.org/I4210145268",
                "ror": "https://ror.org/03se9eg94",
                "display_name": "Hospital das Clínicas da Faculdade de Medicina da Universidade de São Paulo",
                "country_code": "BR",
                "type": "healthcare",
                "relationship": "related"
                },
                {
                "id": "https://openalex.org/I2800423888",
                "ror": "https://ror.org/01whwkf30",
                "display_name": "Instituto Butantan",
                "country_code": "BR",
                "type": "facility",
                "relationship": "related"
                }
            ],
            "counts_by_year": [
                {
                "year": 2023,
                "works_count": 9433,
                "cited_by_count": 287073
                },
                {
                "year": 2022,
                "works_count": 18651,
                "cited_by_count": 484718
                },
                {
                "year": 2021,
                "works_count": 21080,
                "cited_by_count": 485365
                },
                {
                "year": 2020,
                "works_count": 20640,
                "cited_by_count": 403572
                },
                {
                "year": 2019,
                "works_count": 18641,
                "cited_by_count": 324678
                },
                {
                "year": 2018,
                "works_count": 17798,
                "cited_by_count": 280279
                },
                {
                "year": 2017,
                "works_count": 16836,
                "cited_by_count": 248801
                },
                {
                "year": 2016,
                "works_count": 16305,
                "cited_by_count": 235275
                },
                {
                "year": 2015,
                "works_count": 15793,
                "cited_by_count": 245299
                },
                {
                "year": 2014,
                "works_count": 14468,
                "cited_by_count": 208808
                },
                {
                "year": 2013,
                "works_count": 13379,
                "cited_by_count": 188664
                },
                {
                "year": 2012,
                "works_count": 12402,
                "cited_by_count": 166372
                }
            ],
            "roles": [
                {
                "role": "publisher",
                "id": "https://openalex.org/P4365924477",
                "works_count": 2375
                },
                {
                "role": "institution",
                "id": "https://openalex.org/I17974374",
                "works_count": 309714
                },
                {
                "role": "publisher",
                "id": "https://openalex.org/P4310312331",
                "works_count": 87131
                },
                {
                "role": "funder",
                "id": "https://openalex.org/F4320323339",
                "works_count": 698
                }
            ],
            "x_concepts": [
                {
                "id": "https://openalex.org/C86803240",
                "wikidata": "https://www.wikidata.org/wiki/Q420",
                "display_name": "Biology",
                "level": 0,
                "score": 59.8
                },
                {
                "id": "https://openalex.org/C71924100",
                "wikidata": "https://www.wikidata.org/wiki/Q11190",
                "display_name": "Medicine",
                "level": 0,
                "score": 50.9
                },
                {
                "id": "https://openalex.org/C185592680",
                "wikidata": "https://www.wikidata.org/wiki/Q2329",
                "display_name": "Chemistry",
                "level": 0,
                "score": 40.7
                },
                {
                "id": "https://openalex.org/C121332964",
                "wikidata": "https://www.wikidata.org/wiki/Q413",
                "display_name": "Physics",
                "level": 0,
                "score": 35.4
                },
                {
                "id": "https://openalex.org/C126322002",
                "wikidata": "https://www.wikidata.org/wiki/Q11180",
                "display_name": "Internal medicine",
                "level": 1,
                "score": 29.6
                },
                {
                "id": "https://openalex.org/C55493867",
                "wikidata": "https://www.wikidata.org/wiki/Q7094",
                "display_name": "Biochemistry",
                "level": 1,
                "score": 27.7
                },
                {
                "id": "https://openalex.org/C54355233",
                "wikidata": "https://www.wikidata.org/wiki/Q7162",
                "display_name": "Genetics",
                "level": 1,
                "score": 27.4
                },
                {
                "id": "https://openalex.org/C138885662",
                "wikidata": "https://www.wikidata.org/wiki/Q5891",
                "display_name": "Philosophy",
                "level": 0,
                "score": 25.8
                },
                {
                "id": "https://openalex.org/C41008148",
                "wikidata": "https://www.wikidata.org/wiki/Q21198",
                "display_name": "Computer science",
                "level": 0,
                "score": 24.1
                },
                {
                "id": "https://openalex.org/C15744967",
                "wikidata": "https://www.wikidata.org/wiki/Q9418",
                "display_name": "Psychology",
                "level": 0,
                "score": 22.7
                },
                {
                "id": "https://openalex.org/C33923547",
                "wikidata": "https://www.wikidata.org/wiki/Q395",
                "display_name": "Mathematics",
                "level": 0,
                "score": 21.5
                },
                {
                "id": "https://openalex.org/C178790620",
                "wikidata": "https://www.wikidata.org/wiki/Q11351",
                "display_name": "Organic chemistry",
                "level": 1,
                "score": 21.5
                },
                {
                "id": "https://openalex.org/C142724271",
                "wikidata": "https://www.wikidata.org/wiki/Q7208",
                "display_name": "Pathology",
                "level": 1,
                "score": 21.0
                },
                {
                "id": "https://openalex.org/C127413603",
                "wikidata": "https://www.wikidata.org/wiki/Q11023",
                "display_name": "Engineering",
                "level": 0,
                "score": 20.9
                }
            ],
            "works_api_url": "https://api.openalex.org/works?filter=institutions.id:I17974374",
            "updated_date": "2023-07-24T03:31:37.080635",
            "created_date": "2016-06-24"
            },
        }
    """

    if country:
        url = (
            settings.URL_API_OPENALEX_INSTITUTIONS
            + f"?filter=country_code:{country}&per-page=200&cursor=*"
        )
    else:
        url = settings.URL_API_OPENALEX_INSTITUTIONS + f"?per-page=200&cursor=*"

    _source, _ = Source.objects.get_or_create(name="OPENALEX")

    try:
        flag = True
        inst_count = 0

        while flag:
            payload = core_utils.fetch_data(url, json=True, timeout=30, verify=True)

            if payload.get("results"):
                for item in payload.get("results"):
                    inst = {}
                    inst["specific_id"] = item.get("id")
                    inst["display_name"] = item.get("display_name")
                    inst["country_code"] = item.get("country_code")
                    inst["type"] = item.get("type")
                    inst["updated"] = item.get("updated_date")
                    inst["created"] = item.get("created_date")
                    inst["source"] = _source
                    inst["raw"] = item

                    inst, is_created = models.SourceInstitution.create_or_update(**inst)

                    logger.info(
                        "%s: %s"
                        % (
                            "Created institution"
                            if is_created
                            else "Updated institution",
                            inst,
                        )
                    )
                    inst_count += 1

                cursor = payload["meta"]["next_cursor"]

                # Url with new cursor
                url = url.split("cursor=")[0] + "cursor=" + cursor

                if length and (length <= inst_count):
                    flag = False

            else:
                logger.info("No more institution found.")
                return
    except Exception as e:
        logger.info(f"Unexpected error: {e}")


@celery_app.task(name="Update the Institution entity with the matching SourceInstitution")
def update_inst_by_source_inst(user_id, source="MEC"):
    """
    This task update the Sources on Institution bind the translation name on SourceInstitution.

    Update the city of the found institutions.
    """

    for inst in Institution.objects.filter(source=source):

        sinst = SourceInstitution.objects.filter(display_name__icontains=inst.name)
        tsint = InstitutionTranslateName.objects.filter(name__icontains=inst.name, language__code2="pt")
        
        if sinst:
            logger.info("Found instiution: %s" % (sinst[0].display_name))
            inst.sources.add(sinst[0])
            inst.save()
            
        if tsint:
            logger.info("Found instiution: %s" % (tsint[0].name))
            inst.sources.add(tsint[0].source_institution)
            inst.save()
