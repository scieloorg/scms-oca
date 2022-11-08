from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app

from indicator import controller


User = get_user_model()


@celery_app.task(bind=True, name=_("Geração de todos os indicadores de artigos científicos em acesso aberto"))
def task_evolution_of_scientific_production_all(self, creator_id, years_number=None):
    years_number = years_number or 10
    categories = [
        'OPEN_ACCESS_STATUS',
        'USE_LICENSE',
    ]
    for category_id in categories:
        controller.evolution_of_scientific_production(
            creator_id=creator_id,
            category_id=category_id,
            years_range=controller.get_years_range(years_number),
        )
        break

    contexts = [
        'AFFILIATION_UF',
        # 'AFFILIATION',
        # 'THEMATIC_AREA',
    ]
    for category_id in categories:
        for context_id in contexts:
            controller.evolution_of_scientific_production_in_context(
                creator_id=creator_id,
                category_id=category_id,
                years_range=controller.get_years_range(years_number),
                context_id=context_id,
            )
            break


@celery_app.task(bind=True, name=_("Geração de todos os indicadores de ações em Ciência Aberta"))
def task_directory_numbers_all(self, creator_id):
    controller.directory_numbers(
        creator_id,
        category_id='CA_ACTION',
        category2_id=None,
    )
    controller.directory_numbers(
        creator_id,
        category_id="CA_ACTION",
        category2_id="CA_PRACTICE",
    )
    controller.directory_numbers(
        creator_id,
        category_id="CA_ACTION",
        category2_id="THEMATIC_AREA",
    )
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        category2_id="CA_PRACTICE",
        context_id="THEMATIC_AREA",
    )
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        context_id="THEMATIC_AREA",
    )
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        category2_id="CA_PRACTICE",
        context_id="INSTITUTION",
    )
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        context_id="INSTITUTION",
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de periódicos"))
def task_journals_numbers_all(self, creator_id):
    # OK
    categories = [
        'OPEN_ACCESS_STATUS',
        'USE_LICENSE',
        # 'PUBLISHER_UF',
        # 'PUBLISHER',
        # 'THEMATIC_AREA',
    ]
    for category_id in categories:
        controller.journals_numbers(
            creator_id=creator_id,
            category_id=category_id,
        )
