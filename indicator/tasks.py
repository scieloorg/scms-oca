import json
import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from pyalex import Works

from config import celery_app
from core.models import Source
from indicator import indicatorOA, models

User = get_user_model()


@celery_app.task(bind=True, name=_("Generate scientific indicator by OA API"))
def task_generate_indicators_by_oa_api(self, user_id, indicators):
    """
    This task receive a indicators list, something like:

    [
        {
            "title": "Quantidade de documentos entre os anos de 2014 até 2024",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no perído de 2014 até 2024",
            "group_by": "type",
            "filters": {"is_oa": True},
            "range_year": {
                "start": 2014,
                "end": 2024
            }
        }
    ]

    Each item in the list is a param to generate a indicator.
    """

    user = User.objects.get(id=user_id)

    for indicator in indicators:
        serie_list = []
        result_dict = {}
        start = indicator.get("range_year").get("start")
        end = indicator.get("range_year").get("end") + 1

        for year in range(start, end):
            result, meta = (
                Works()
                .filter(**indicator.get("filters"))
                .filter(publication_year=year)
                .group_by(indicator.get("group_by"))
                .get(return_meta=True)
            )
            logging.info(meta)

            if indicator.get("stacked"):

                for item in result:
                    key_display_name = item["key_display_name"]
                    count = item["count"]
                    result_dict.setdefault(key_display_name, [])
                    result_dict[key_display_name].append(count)

            else:
                serie_list.append(result[0].get("count"))
                serie_json = json.dumps(
                    {
                        "keys": [key for key in range(start, end)],
                        "series": {"data": serie_list, "type": "bar"},
                    }
                )

        if indicator.get("stacked"):
            for serie_name_and_stack, data in result_dict.items():
                serie_list.append(
                    {
                        "name": serie_name_and_stack.title(),
                        "type": "bar",
                        "stack": serie_name_and_stack.title(),
                        "emphasis": {"focus": "series"},
                        "data": data,
                    }
                )

            serie_json = json.dumps(
                {"keys": [key for key in range(start, end)], "series": serie_list}
            )

        indicator_model = models.Indicator(
            title=indicator.get("title"),
            creator=user,
            summarized=serie_json,
            record_status="PUBLISHED",
            description=indicator.get("description"),
        )

        indicator_model.save()


@celery_app.task(bind=True, name=_("Generate data from OA(OpenAlex) Count Regions"))
def task_generate_indicators_by_oa_api_regions(
    self,
    user_id,
    name="OA World Count Regions",
    data_type="count_regions",
    source="OPENALEX",
    start_year=2014,
    end_year=2023,
):
    """
    This task process the data from OpenAlex.

    Stored the data on IndicatorData with data_type: regions_count and raw data with something like:
        {"Western Europe": [ "AD", "AT", "BE", "BV", "CY", "DK", "FO", "FI", "FR", "DE", "GI", "GR", "GL", "GG", "VA", "IS", "IE", "IM", "IT", "JE", "LI", "LU", "MT", "MC", "NL", "NO", "PT", "SM", "ES", "SJ", "SE", "CH", "GB", "AX", ]}
    """

    source, source_id = Source.objects.get_or_create(name=source)

    result = indicatorOA.Indicator(
        filters={},
        group_by="publication_year",
        range_filter={
            "filter_name": "year",
            "range": {"start": start_year, "end": end_year},
        },
    ).generate_by_region()

    models.IndicatorData.objects.update_or_create(
        name=name, data_type=data_type, source=source, raw=result
    )


@celery_app.task(bind=True, name=_("Generate data from OA(OpenAlex) Count Countries"))
def task_generate_indicators_by_oa_api_countries(
    self,
    user_id,
    name="OA World Count Countries",
    data_type="count_countries",
    source="OPENALEX",
    start_year=2014,
    end_year=2023,
):
    """
    This task process the data from OpenAlex.

    Stored the data on IndicatorData with data_type: countries_count and raw data with something like:

        { 'us': { '2023': 449364, '2022': 454245, '2021': 514552, '2020': 504690, '2019': 431683, '2018': 399696, '2015': 332322, '2014': 280477, '2017': 370061, '2016': 335551}, 'ch': { '2023': 2504273, '2022': 2367105, '2021': 2161980, '2020': 1944761, '2019': 1670192, '2018': 1482810, '2016': 1181621, '2017': 1310592, '2014': 1260167, '2015': 1217707} } }
    """

    source, source_id = Source.objects.get_or_create(name=source)

    result = indicatorOA.Indicator(
                filters={},
                group_by="publication_year",
                range_filter={
                    "filter_name": "year",
                    "range": {"start": start_year, "end": end_year},
                },
            ).generate_by_country()

    models.IndicatorData.objects.update_or_create(
        name=name, data_type=data_type, source=source, raw=result
    )
