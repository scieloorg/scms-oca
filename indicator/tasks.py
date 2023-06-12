from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app

from indicator import controller
from indicator import directory


User = get_user_model()


@celery_app.task(
    bind=True, name=_("Geração de indicadores de ações em Ciência Aberta com contexto")
)
def task_generate_directory_numbers_with_context(
    self,
    creator_id,
    context_id,
):
    return controller.generate_directory_numbers_with_context(
        creator_id,
        context_id,
    )


@celery_app.task(
    bind=True, name=_("Geração de indicadores de ações em Ciência Aberta sem contexto")
)
def task_generate_directory_numbers_without_context(
    self,
    creator_id,
    category2_id=None,
):
    return controller.generate_directory_numbers_without_context(
        creator_id,
        category2_id,
    )


@celery_app.task(
    bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto")
)
def task_generate_evolution_of_scientific_production(
    self,
    creator_id,
    category_id,
    initial_year,
    final_year,
    context_params=None,
    context_id=None,
):
    controller.evolution_of_scientific_production(
        creator_id=creator_id,
        category_id=category_id,
        years_range=range(initial_year, final_year + 1),
        context_params=context_params,
        context_id=context_id,
    )

@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta"))
def task_generate_directory_indicators(
    self, creator_id, action_name=None, filter_by=None, group_by=None
):
    creator = User.objects.get(id=creator_id) or User.objects.first()
    action__names = [action_name]

    filter_params = [{}]
    if filter_by == "thematic_area":
        filter_params = directory.get_thematic_area_filter_params()
    elif filter_by == "location":
        filter_params = directory.get_location_filter_params()

    group_by = group_by or {}

    directory.generate_indicators(creator, action__names, filter_params, group_by)