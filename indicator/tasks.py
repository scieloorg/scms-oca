import json
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.contrib.contenttypes.models import ContentType

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
def task_generate_article_indicators(self, user_id, indicators):
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
        
        # check if the indicator file existe and if ids is not empty.
        if not models.IndicatorFile.objects.filter(
            data_ids=ind.get_ids()
        ):
            
            indicator_model = models.Indicator(
                title=ind.title,
                creator=user,
                summarized=serie_json,
                record_status= "PUBLISHED" if ind.get_ids() else "NOT PUBLISHED",
                description=ind.description,
            )

            indicator_model.save()
            # items = []

            # for model in ind.models:
            #     ct = ContentType.objects.get(model=model)
            #     md = ct.model_class()
            #     items += md.objects.filter(pk__in=[id for id in ind.ids.keys()])

            # indicator_model.save_raw_data(items=items, ids=ind.get_ids())
