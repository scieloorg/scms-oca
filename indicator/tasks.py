from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app

from indicator import controller


User = get_user_model()


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta com contexto"))
def task_generate_directory_numbers_with_context(
        self,
        creator_id,
        context_id,
        ):
    return controller.generate_directory_numbers_with_context(
            creator_id,
            context_id,
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta sem contexto"))
def task_generate_directory_numbers_without_context(
        self,
        creator_id,
        category2_id=None,
        ):
    return controller.generate_directory_numbers_without_context(
            creator_id,
            category2_id,
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto"))
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
        years_range=range(initial_year, final_year+1),
        context_params=context_params,
        context_id=context_id,
    )


##############################################################################
@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto x"))
def task_evolution_of_scientific_production(self, creator_id, category1, context_id=None, years_number=None):
    if category1 not in ['OPEN_ACCESS_STATUS', 'USE_LICENSE']:
        raise ValueError("Expected category1 values: OPEN_ACCESS_STATUS, USE_LICENSE")
    years_number = years_number or 10

    if not context_id:
        return controller.evolution_of_scientific_production(
            creator_id=creator_id,
            category_id=category1,
            years_range=controller.get_years_range(years_number),
        )

    if context_id in ['AFFILIATION', 'AFFILIATION_UF', ]:
        return controller.evolution_of_scientific_production_in_context(
            creator_id=creator_id,
            category_id=category1,
            years_range=controller.get_years_range(years_number),
            context_id=context_id,
        )
    raise ValueError("Expected context_id values: AFFILIATION, AFFILIATION_UF")


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta old"))
def task_directory_numbers(self, creator_id, category2=None, context_id=None):
    category1 = 'CA_ACTION'
    if category2 and category2 not in ['CA_PRACTICE', 'THEMATIC_AREA']:
        raise ValueError(
            "Expected category2 values: CA_PRACTICE, THEMATIC_AREA")

    if context_id:
        if context_id not in ['INSTITUTION', 'LOCATION', 'THEMATIC_AREA']:
            raise ValueError(
                "Expected context_id values: INSTITUTION, LOCATION, THEMATIC_AREA")
        return controller.directory_numbers_in_context(
            creator_id,
            category_id=category1,
            category2_id=category2,
            context_id=context_id,
        )
    return controller.directory_numbers(
        creator_id,
        category_id=category1,
        category2_id=category2,
    )


##############################################################################
@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto por tipo"))
def task_evolution_of_scientific_production__open_access_status(self, creator_id, years_number=None):
    years_number = years_number or 10
    controller.evolution_of_scientific_production(
        creator_id=creator_id,
        category_id='OPEN_ACCESS_STATUS',
        years_range=controller.get_years_range(years_number),
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto por tipo em contexto geográfico UF"))
def task_evolution_of_scientific_production__open_access_status__uf(self, creator_id, years_number=None):
    years_number = years_number or 10
    controller.evolution_of_scientific_production_in_context(
        creator_id=creator_id,
        category_id='OPEN_ACCESS_STATUS',
        years_range=controller.get_years_range(years_number),
        context_id='AFFILIATION_UF',
    )

@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto por tipo em contexto institucional"))
def task_evolution_of_scientific_production__open_access_status__institution(self, creator_id, years_number=None):
    years_number = years_number or 10
    controller.evolution_of_scientific_production_in_context(
        creator_id=creator_id,
        category_id='OPEN_ACCESS_STATUS',
        years_range=controller.get_years_range(years_number),
        context_id='AFFILIATION',
    )

##############################################################################
@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto por licença de uso"))
def task_evolution_of_scientific_production__use_license(self, creator_id, years_number=None):
    years_number = years_number or 10
    controller.evolution_of_scientific_production(
        creator_id=creator_id,
        category_id='USE_LICENSE',
        years_range=controller.get_years_range(years_number),
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto por licença de uso em contexto geográfico UF"))
def task_evolution_of_scientific_production__use_license__uf(self, creator_id, years_number=None):
    years_number = years_number or 10
    controller.evolution_of_scientific_production_in_context(
        creator_id=creator_id,
        category_id='USE_LICENSE',
        years_range=controller.get_years_range(years_number),
        context_id='AFFILIATION_UF',
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos em acesso aberto por licença de uso em contexto institucional"))
def task_evolution_of_scientific_production__use_license__institution(self, creator_id, years_number=None):
    years_number = years_number or 10
    controller.evolution_of_scientific_production_in_context(
        creator_id=creator_id,
        category_id='USE_LICENSE',
        years_range=controller.get_years_range(years_number),
        context_id='AFFILIATION',
    )


##############################################################################
@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta no Brasil"))
def task_directory_numbers__action(self, creator_id):
    controller.directory_numbers(
        creator_id,
        category_id='CA_ACTION',
        category2_id=None,
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta em contexto de área temática"))
def task_directory_numbers__action__in_thematic_area(self, creator_id):
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        context_id="THEMATIC_AREA",
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta em contexto de instituição"))
def task_directory_numbers__action__in_institution(self, creator_id):
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        context_id="INSTITUTION",
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta em UF"))
def task_directory_numbers__action__in_UF(self, creator_id):
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        context_id="LOCATION",
    )


##############################################################################
@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta por Prática"))
def task_directory_numbers__action_and_practice(self, creator_id):
    controller.directory_numbers(
        creator_id,
        category_id="CA_ACTION",
        category2_id="CA_PRACTICE",
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta por Prática em áreas temáticas"))
def task_directory_numbers__action_and_practice__in_thematic_area(self, creator_id):
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        category2_id="CA_PRACTICE",
        context_id="THEMATIC_AREA",
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta por Prática em instituições"))
def task_directory_numbers__action_and_practice__in_institution(self, creator_id):
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        category2_id="CA_PRACTICE",
        context_id="INSTITUTION",
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta por Prática em UF"))
def task_directory_numbers__action_and_practice__in_UF(self, creator_id):
    controller.directory_numbers_in_context(
        creator_id,
        category_id="CA_ACTION",
        category2_id="CA_PRACTICE",
        context_id="LOCATION",
    )


##############################################################################
@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta por Área temática"))
def task_directory_numbers__action_and_thematic_area(self, creator_id):
    controller.directory_numbers(
        creator_id,
        category_id="CA_ACTION",
        category2_id="THEMATIC_AREA",
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta por Área temática em UF"))
def task_directory_numbers__action_and_thematic_area__in_uf(self, creator_id):
    controller.directory_numbers(
        creator_id,
        category_id="CA_ACTION",
        category2_id="THEMATIC_AREA",
        context_id="LOCATION"
    )


@celery_app.task(bind=True, name=_("Geração de indicadores de ações em Ciência Aberta por Área temática em instituição"))
def task_directory_numbers__action_and_thematic_area__in_institution(self, creator_id):
    controller.directory_numbers(
        creator_id,
        category_id="CA_ACTION",
        category2_id="THEMATIC_AREA",
        context_id="INSTITUTION"
    )


##############################################################################
@celery_app.task(bind=True, name=_("Geração de indicadores de periódicos"))
def task_journals_numbers_all(self, creator_id):
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
