import json
import logging

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _
from pyalex import Works

from config import celery_app
# from indicator import directory, sciprod
from indicator import indicator, models

User = get_user_model()


# @celery_app.task(bind=True, name=_("Geração de indicadores de ações"))
# def task_generate_directory_indicators(
#     self, user_id, creator_id, action_name=None, filter_by=None, group_by=None
# ):
#     creator = User.objects.get(id=creator_id) or User.objects.first()
#     action__names = [action_name]

#     group_by = group_by or {}

#     directory.generate_indicators(creator, action__names, filter_by, group_by)


# @celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos"))
# def task_generate_sciprod_indicators(
#     self, user_id, creator_id, filter_by=None, group_by=None, begin_year=None, end_year=None,
# ):
#     creator = User.objects.get(id=creator_id) or User.objects.first()

#     group_by = group_by or {}

#     sciprod.generate_indicators(creator, filter_by, group_by, begin_year, end_year)


@celery_app.task(bind=True, name=_("Generate scientific indicator"))
def task_generate_article_indicators(self, user_id, indicators, remove=False, raw_data=False):
    """
    This task receive a indicators list, something like:

    [
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos com e sem APC por instituição 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["institutions", "apc"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023},
            "model": "article"
        }
    ]

    Each item in the list is a param to generate a indicator.
    """

    user = User.objects.get(id=user_id)

    if remove: 
        models.Indicator.objects.all().delete()
        models.IndicatorFile.objects.all().delete()

    for ind in indicators:
        ind = indicator.Indicator(**ind)
        serie_list = []

        for item in ind.generate():
            for serie_name_and_stack, data in item.items():
                if data:
                    if "-" in serie_name_and_stack:
                        stack = " ".join(serie_name_and_stack.split("-")[1:])
                    else:
                        stack = serie_name_and_stack

                    serie_list.append(
                        {
                            "name": serie_name_and_stack,
                            "type": "bar",
                            "stack": stack,
                            "emphasis": {"focus": "series"},
                            "data": list(data.get("counts")),
                            # "label": {"show": "true"},
                        }
                    )

        serie_json = json.dumps(
            {"keys": [key for key in ind.get_keys()], "series": serie_list}
        )

        indicator_model = models.Indicator(
            title=ind.title,
            creator=user,
            summarized=serie_json,
            record_status="PUBLISHED",
            description=ind.description,
        )
        
        indicator_model.save()

        if raw_data:
            for data in ind.get_data(rows=10000, files_by_year=True):
                files = {}

                file_name_jsonl = "%s.json" % (data[0])
                file_path_jsonl = ind.save_jsonl(
                    data[1], dir_name="/tmp", file_name=file_name_jsonl
                )

                file_name_csv = "%s.csv" % (data[0])
                file_path_csv = ind.save_csv(
                    data[1], dir_name="/tmp", file_name=file_name_csv
                )
                files.update(
                    {file_name_csv: file_path_csv, file_name_jsonl: file_path_jsonl}
                )

                for file_name, file_path in files.items():
                    try: 
                        ind_file = models.IndicatorFile(name=file_name)
                        zfile = open(file_path, "rb")
                        ind_file.raw_data.save(file_name + ".zip", zfile)
                        ind_file.save()

                        indicator_model.indicator_file.add(ind_file)
                    except TypeError as e: 
                        logging.info("Error on save file to indicator: %s, %s" % (file_name, file_path))

                    


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
        result_dict = {}
        serie_list = []
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
            for item in result:
                key_display_name = item["key_display_name"]
                count = item["count"]
                result_dict.setdefault(key_display_name, [])
                result_dict[key_display_name].append(count)

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

