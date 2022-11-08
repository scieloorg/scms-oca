from datetime import datetime
import logging
import csv
import io
import json

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Count, Sum, Q
from django.utils.translation import gettext as _
from django.core.exceptions import FieldError

from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory

from scholarly_articles.models import ScholarlyArticles, Affiliations
from location.models import Location
from institution.models import Institution
from usefulmodels.models import Practice, State, Action, Country, ThematicArea
from .models import Indicator, ActionAndPractice, ScientificProduction
from . import choices


User = get_user_model()


OA_STATUS_ITEMS = ('gold', 'bronze', 'green', 'hybrid', )

CATEGORIES = {
    'OPEN_ACCESS_STATUS': {
        'title': 'tipo',
        'name': 'tipo de acesso aberto',
        'category_attributes': ['open_access_status']},
    'USE_LICENSE': {
        'title': 'licença de uso',
        'name': 'licença de uso',
        'category_attributes': ['use_license']},
    'CA_ACTION': {
        'title': 'ações',
        'name': 'ação',
        'category_attributes': ['action__name', 'classification']},
    'CA_PRACTICE': {
        'title': 'prática',
        'name': 'prática',
        'category_attributes': ['practice__name']},
    'THEMATIC_AREA': {
        'name': 'área temática',
        'title': 'área temática',
        'category_attributes': [
            'thematic_areas__level0',
        ]},
}


CONTEXTS = {
    'AFFILIATION_UF': {
        'title': '',
        'type': choices.GEOGRAPHIC,
        'preposition': "-",
        'name': 'contributors__affiliation__official__location__state',
        'category_attributes': [
            'contributors__affiliation__official__location__state__name',
            'contributors__affiliation__official__location__state__acronym'
        ]},
    'AFFILIATION': {
        'title': 'instituição',
        'type': choices.INSTITUTIONAL,
        'preposition': "-",
        'name': 'institution',
        'category_attributes': [
            'contributors__affiliation__official__name',
            'contributors__affiliation__official__level_1',
            'contributors__affiliation__official__level_2',
            'contributors__affiliation__official__level_3',
            'contributors__affiliation__official__location__city__name',
            'contributors__affiliation__official__location__state__name',
            'contributors__affiliation__official__location__state__acronym'
        ]},
    'THEMATIC_AREA': {
        'name': 'área temática',
        'type': choices.THEMATIC,
        'preposition': "-",
        'category_attributes': [
            'thematic_areas__level0',
        ]},
    'LOCATION': {
        'title': '',
        'type': choices.GEOGRAPHIC,
        'preposition': "-",
        'name': 'locations__state',
        'category_attributes': [
                'locations__state__name',
                'locations__state__acronym',
            ],
        'category_attributes_options': [[
                'institutions__location__state__name',
                'institutions__location__state__acronym',
            ], [
                'locations__state__name',
                'locations__state__acronym',
            ], [
                'organization__location__state__name',
                'organization__location__state__acronym',
            ]
        ]},
    'INSTITUTION': {
        'title': 'instituição',
        'type': choices.INSTITUTIONAL,
        'preposition': "-",
        'name': 'institution',
        'category_attributes': [
            'institutions__name',
            'institutions__level_1',
            'institutions__level_2',
            'institutions__level_3',
            'institutions__location__city__name',
            'institutions__location__state__acronym',
            ],
        'category_attributes_options': [[
            'institutions__name',
            'institutions__level_1',
            'institutions__level_2',
            'institutions__level_3',
            'institutions__location__city__name',
            'institutions__location__state__acronym',
            ],
            [
            'organization__name',
            'organization__level_1',
            'organization__level_2',
            'organization__level_3',
            'organization__location__city__name',
            'organization__location__state__acronym',
            ]]},
    # 'PUBLISHER_UF': {
    #     'title': 'instituição',
    #     'name': 'institution',
    #     'name': 'UF',
    #     'category_attributes': ['publisher__location__state__acronym']},
    # 'PUBLISHER': {
    #     'title': 'instituição',
    #     'name': 'institution',
    #     'category_attributes': [
    #         'publisher__name',
    #         'publisher__level_1',
    #         'publisher__level_2',
    #         'publisher__level_3',
    #         'publisher__location__city__name',
    #         'publisher__location__state__acronym']},

}


def _add_category_name(items, cat1_attributes, cat1_name=None, cat2_attributes=None, cat2_name=None):
    cat1_name = cat1_name or "name"
    for item in items:
        logging.info(item)
        if item['count']:
            item.update({
                cat1_name: _concat_values(cat1_attributes, item.copy(), " | "),
                "count": item['count'],
            })
            if cat2_attributes and cat2_name:
                item[cat2_name] = _concat_values(cat2_attributes, item.copy(), " | ")
            yield item


def delete():
    for item in Indicator.objects.iterator():
        try:
            item.action_and_practice = None
            if item.thematic_areas:
                item.thematic_areas.clear()
            if item.institutions:
                item.institutions.clear()
            if item.locations:
                item.locations.clear()
            item.delete()
        except Exception as e:
            logging.exception(e)


def _add_param(params, name, value):
    if value:
        params[name] = value
    else:
        params[f'{name}__isnull'] = True


def _add_param_for_action_and_practice(params, action_and_practice):
    if action_and_practice:
        _add_param(params, "action_and_practice__action", action_and_practice.action)
        _add_param(params, "action_and_practice__classification", action_and_practice.classification)
        _add_param(params, "action_and_practice__practice", action_and_practice.practice)
    else:
        _add_param(params, "action_and_practice", None)


def _add_param_for_thematic_areas(params, thematic_areas):
    if thematic_areas:
        for item in thematic_areas.iterator():
            _add_param(params, "thematic_areas__level0", item.level0)
            _add_param(params, "thematic_areas__level1", item.level1)
            _add_param(params, "thematic_areas__level2", item.level2)
            break
    else:
        _add_param(params, "thematic_areas", None)


def _add_param_for_institutions(params, institutions):
    if institutions:
        for item in institutions.iterator():
            _add_param(params, "institutions__name", item.name)
    else:
        _add_param(params, "institutions", None)


def _add_param_for_locations(params, locations):
    if locations:
        for item in locations.iterator():
            _add_param(params, "locations__city__name", item.city__name)
            _add_param(params, "locations__state__acronym", item.state__acronym)
            _add_param(params, "locations__country__acron2", item.country__acron2)
    else:
        _add_param(params, "locations", None)


def get_indicator_parameters(indicator):
    if indicator:
        d = dict(
            title=indicator.title,
            scope=indicator.scope,
            measurement=indicator.measurement,
            creator_id=indicator.creator_id,
            scientific_production=indicator.scientific_production,
            keywords=indicator.keywords,
            start_date_year=indicator.start_date_year,
            end_date_year=indicator.end_date_year,
            action=None,
            classification=None,
            practice=None,
        )
        if indicator.action_and_practice:
            d.update(dict(
                action=indicator.action_and_practice.action,
                classification=indicator.action_and_practice.classification,
                practice=indicator.action_and_practice.practice,
            ))
        return d


def get_latest_version(
        title,
        action,
        classification,
        practice,
        scope,
        measurement,
        creator_id,
        scientific_production=None,
        keywords=None,
        start_date_year=None,
        end_date_year=None,
        ):
    """
    Obtém a versão mais recente de uma instância de Indicator,

    Parameters
    ----------
    action : Action
    classification : str
    practice : Practice
    scope : choices.SCOPE
    measurement : choices.MEASUREMENT_TYPE
    """

    params = dict(
        scope=scope,
        measurement=measurement,
        posterior_record__isnull=True
    )
    _add_param(params, 'title', title)
    _add_param(params, 'scientific_production', scientific_production)
    _add_param(params, 'start_date_year', start_date_year)
    _add_param(params, 'end_date_year', end_date_year)

    if any([action, classification, practice]):
        action_and_practice = ActionAndPractice.get_or_create(
            action, classification, practice
        )
    else:
        action_and_practice = None

    try:
        return Indicator.objects.filter(**params)[0]
    except Exception as e:
        return None


def create_record(
        title,
        action,
        classification,
        practice,
        scope,
        measurement,
        creator_id,
        scientific_production=None,
        start_date_year=None,
        end_date_year=None,
        keywords=None,
        ):
    """
    Cria uma nova instância de Indicator,
    adicionando / atualizando os atributos `seq` e outros relacionados com
    a versão do indicador

    Parameters
    ----------
    action : Action
    classification : str
    practice : Practice
    scope : choices.SCOPE
    measurement : choices.MEASUREMENT_TYPE
    """
    latest = get_latest_version(
            title,
            action,
            classification,
            practice,
            scope,
            measurement,
            creator_id,
            scientific_production,
            keywords,
            start_date_year,
            end_date_year,
        )
    if latest:
        previous = latest
        seq = (previous.seq or 0) + 1
        previous.validity = choices.OUTDATED
        action_and_practice = latest.action_and_practice
    else:
        seq = 1
        previous = None
        if any([action, classification, practice]):
            action_and_practice = ActionAndPractice.get_or_create(
                action, classification, practice
            )
        else:
            action_and_practice = None

    logging.info("Create Indicator")
    indicator = Indicator()
    indicator.seq = seq
    indicator.previous_record = previous
    indicator.posterior_record = None
    indicator.title = title
    indicator.validity = choices.CURRENT
    indicator.action_and_practice = action_and_practice
    indicator.scope = scope
    indicator.measurement = measurement
    indicator.scientific_production = scientific_production
    indicator.start_date_year = start_date_year
    indicator.end_date_year = end_date_year
    indicator.record_status = choices.PUBLISHED
    indicator.creator_id = creator_id
    indicator.save()

    if keywords:
        indicator.keywords.add(*keywords)
    indicator.save()

    if previous:
        previous.posterior_record = indicator
        previous.save()

    #indicator.code = build_code(indicator)
    indicator.save()
    return indicator


##############################################################################
def directory_numbers(
        creator_id,
        category_id,
        category2_id=None,
        ):

    preposition = _("no Brasil")

    category_title = CATEGORIES[category_id]['title']
    category_name = CATEGORIES[category_id]['name']
    category_attributes = CATEGORIES[category_id]['category_attributes']
    category_attributes_options = CATEGORIES[category_id].get('category_attributes_options')
    title = "Número de {} em Ciência Aberta".format(category_title)
    cat_attributes = category_attributes.copy()

    if category2_id:
        category2_title = CATEGORIES[category2_id]['title']
        category2_name = CATEGORIES[category2_id]['name']
        category2_attributes = CATEGORIES[category2_id]['category_attributes']
        category2_attributes_options = CATEGORIES[category2_id].get('category_attributes_options')
        title = "Número de {} em Ciência Aberta por {}".format(category_title, category2_title)
        cat_attributes += category2_attributes

    title += f" {preposition} "

    scope = choices.GENERAL
    measurement = choices.FREQUENCY

    items = []
    items.extend(_directory_numbers(EducationDirectory.objects, cat_attributes))
    items.extend(_directory_numbers(EventDirectory.objects, cat_attributes))
    items.extend(_directory_numbers(InfrastructureDirectory.objects, cat_attributes))
    items.extend(_directory_numbers(PolicyDirectory.objects, cat_attributes))
    indicator = create_record(
        title=title,
        action=None,
        classification=None,
        practice=None,
        scope=scope,
        measurement=measurement,
        creator_id=creator_id,
        keywords=[_('Brasil')],
    )
    indicator.save_raw_data(
        list(EducationDirectory.objects.iterator()) +
        list(EventDirectory.objects.iterator()) +
        list(InfrastructureDirectory.objects.iterator()) +
        list(PolicyDirectory.objects.iterator())
    )
    if category2_id:
        # cat1 = variável cujo valor é comum nos registros
        # por ex, year, practice__name
        indicator.summarized = {
            'items': list(_add_category_name(
                items,
                category_attributes, category_name,
                category2_attributes, category2_name)),
            'cat1_name': category_name,
            'cat2_name': category2_name,
        }
    else:
        indicator.summarized = {
            "items": list(
                _add_category_name(
                    items, category_attributes, category_name)),
            "cat1_name": category_name,
        }
    # indicator.total = len(items)
    indicator.creator_id = creator_id
    indicator.save()


def _get_directory_contexts(context_id):
    """
    Obtém os dados dos contextos (lista de instituições ou UF ou áreas temáticas)
    coletados de todos os diretórios
    """
    contexts = {}
    for model in (EducationDirectory, EventDirectory, InfrastructureDirectory, PolicyDirectory):
        for context_item in _directory_numbers_contexts(model, context_id):
            key = tuple(context_item.values())
            contexts.setdefault(key, [])
            contexts[key].append((model, context_item))
    return contexts


def _directory_numbers(dataset, category_attributes):
    return dataset.values(
            *category_attributes
        ).annotate(
            count=Count('id')
        ).order_by('count').iterator()


def directory_numbers_in_context(
        creator_id,
        category_id,
        category2_id=None,
        context_id=None,
        ):
    category_title = CATEGORIES[category_id]['title']
    category_name = CATEGORIES[category_id]['name']
    category_attributes = CATEGORIES[category_id]['category_attributes']
    category_attributes_options = CATEGORIES[category_id].get('category_attributes_options')
    title = "Número de {} em Ciência Aberta".format(category_title)
    cat_attributes = category_attributes.copy()

    if category2_id:
        category2_title = CATEGORIES[category2_id]['title']
        category2_name = CATEGORIES[category2_id]['name']
        category2_attributes = CATEGORIES[category2_id]['category_attributes']
        category2_attributes_options = CATEGORIES[category2_id].get('category_attributes_options')
        title = "Número de {} em Ciência Aberta por {}".format(category_title, category2_title)
        cat_attributes += category2_attributes

    scope = choices.GENERAL
    measurement = choices.FREQUENCY

    for models_contexts in _get_directory_contexts(context_id).values():
        datasets = []
        items = []
        keywords = []
        for model, context_params in models_contexts:
            filters = {}
            for name, value in context_params.items():
                _add_param(filters, name, value)
            dataset = model.objects.filter(**filters)
            datasets.append(dataset)
            items.extend(_directory_numbers(dataset, cat_attributes))

            logging.info(context_params)
            keywords = list([v for v in context_params.values() if v])

        indicator_title = title
        if keywords:
            indicator_title += (
                " " + CONTEXTS[context_id]['preposition'] +
                " " + ", ".join(keywords)
            )
        indicator = create_record(
            title=indicator_title,
            action=None,
            classification=None,
            practice=None,
            scope=scope,
            measurement=measurement,
            creator_id=creator_id,
            keywords=keywords
        )
        indicator.save_raw_data(datasets_iterator(datasets))

        if category2_id:
            # cat2: variável em comum nos diretórios
            # por ex: year, practice__name
            indicator.summarized = {
                'items': list(_add_category_name(
                    items,
                    category_attributes, category_name,
                    category2_attributes, category2_name,
                    )),
                'cat1_name': category_name,
                'cat2_name': category2_name,
            }
        else:
            indicator.summarized = {
                'items': list(_add_category_name(
                    items,
                    category_attributes, category_name,
                    )),
                'cat1_name': category_name,
            }
        # indicator.total = len(items)
        indicator.creator_id = creator_id
        indicator.save()


def datasets_iterator(datasets):
    for dataset in datasets:
        yield from dataset.iterator()


def _directory_numbers_contexts(model, context_id):
    """
    Obtém dados do contexto (INSTITUTION, LOCATION, THEMATIC_AREA, ...)
    de registros do tipo Directory, ou seja, uma lista de dicionários com dados
    de instituições ou localizações ou áreas temáticas registradas no diretório
    """
    category_attributes_options = (
        CONTEXTS[context_id].get('category_attributes_options') or
        [CONTEXTS[context_id]['category_attributes']])
    for category_attributes_option in category_attributes_options:
        try:
            for item in model.objects.values(
                        *category_attributes_option
                    ).annotate(
                        count=Count('id', distinct=True)
                    ).order_by('count').iterator():
                item.pop('count')
                yield item
        except FieldError:
            continue


def _standardize_item(items):
    for item in items:
        for k, v in item.items():
            if 'organization' in k:
                item[k.replace('organization', 'institutions')] = v
            yield item


##########################################################################

def journals_numbers(
        creator_id,
        category_id,
        ):

    category_title = CATEGORIES[category_id]['title']
    category_name = CATEGORIES[category_id]['name']
    category_attributes = CATEGORIES[category_id]['category_attributes']

    action, classification, practice = (
        _get_scientific_production__action_classification_practice())

    observation = 'journal'

    # seleciona produção científica brasileira e de acesso aberto
    # scope = choices.INSTITUTIONAL
    # measurement = choices.FREQUENCY

    scientific_production = ScientificProduction.get_or_create(
        communication_object='journal',
        open_access_status=None,
        use_license=None,
        apc=None,
    )

    title = "Número de periódicos em acesso aberto por {}".format(
        category_title,
    )
    indicator = create_record(
        title=title,
        action=action,
        classification=classification,
        practice=practice,
        scope=choices.GENERAL,
        measurement=choices.FREQUENCY,
        creator_id=creator_id,
        scientific_production=scientific_production,
        start_date_year=datetime.now().year,
    )

    dataset, summarized = _journals_numbers(category_attributes)
    indicator.save_raw_data(dataset.iterator())
    indicator.summarized = {
        "items": list(_add_category_name(
                summarized, category_attributes)),
    }
    # indicator.total = len(indicator.summarized['items'])
    indicator.creator_id = creator_id
    indicator.save()


def _journals_numbers(
        category_attributes,
        ):
    articles_cat = (['open_access_status'], ['use_license'], )

    if category_attributes not in articles_cat:
        raise NotImplementedError(
            "Não implementado para %s" % category_attributes)

    filtered = ScholarlyArticles.objects.filter(
        open_access_status__in=OA_STATUS_ITEMS
    )
    summarized = filtered.values(
            *category_attributes
        ).annotate(
            count=Count("journal", distinct=True)
        )
    return filtered, summarized.order_by('count').iterator()


##########################################################################

def _get_scientific_production__action_classification_practice():
    # identifica action, classification, practice
    action = Action.objects.get(name__icontains='produção')
    practice = Practice.objects.get(name='literatura em acesso aberto')
    classification = "literatura científica"
    return action, classification, practice


def get_years_range(years_number=5):
    return list(range(
            datetime.now().year - years_number,
            datetime.now().year + 1))


def str_years_list(years_range):
    return [str(y) for y in years_range]

##########################################################################


def _concat_values(category_names, category_values, sep=", "):
    return sep.join([
                category_values[k]
                for k in category_names
                if category_values.get(k)
            ])


def evolution_of_scientific_production_in_context(
        creator_id,
        category_id,
        years_range,
        context_id,
        ):
    years_as_str = str_years_list(years_range)

    for context_items in _get_context_items(
            CONTEXTS[context_id]['category_attributes'], years_as_str):
        context_items.pop('count')
        context_params = context_items

        context_data = _get_context_data(
            context_params, CONTEXTS[context_id]['type'])

        evolution_of_scientific_production(
            creator_id,
            category_id,
            years_range,
            context_params,
            context_id,
        )


def _get_context_items(context_params, years_as_str):
    return ScholarlyArticles.objects.filter(
            Q(contributors__affiliation__official__location__country__acron2='BR') |
            Q(contributors__affiliation__country__acron2='BR'),
            open_access_status__in=OA_STATUS_ITEMS,
            year__in=years_as_str,
        ).values(
            *context_params
        ).annotate(
            count=Count('id', distinct=True)
        ).iterator()


def _get_context_data(context_params, context_type):
    # thematic_areas=thematic_areas,
    # institutions=institutions,
    # locations=locations,
    thematic_areas = {}
    institutions = {}
    locations = {}
    params = {}

    # if context_type == choices.THEMATIC:
    #     # TODO
    #     continue

    # if context_type == choices.GEOGRAPHIC:
    #     # TODO
    #     continue

    # if context_type == choices.INSTITUTIONAL:
    #     # TODO
    #     continue
    # return params


def evolution_of_scientific_production(
        creator_id,
        category_id,
        years_range,
        context_params=None,
        context_id=None,
        ):

    category_title = CATEGORIES[category_id]['title']
    category_name = CATEGORIES[category_id]['name']
    category_attributes = CATEGORIES[category_id]['category_attributes']

    # parametros de contexto
    context_params = context_params or {}
    keywords = list([v for v in context_params.values() if v])

    # nome da categoria, obtido da concatenação dos nomes de vários atributos
    if category_name in category_attributes:
        category_name = "_".join(category_attributes)

    # identifica action, classification, practice
    action, classification, practice = (
        _get_scientific_production__action_classification_practice())

    # características do indicador
    scope = choices.CHRONOLOGICAL
    measurement = choices.EVOLUTION
    observation = 'journal-article'

    # característica da produção científica
    scientific_production = ScientificProduction.get_or_create(
        communication_object='journal-article',
        open_access_status=None,
        use_license=None,
        apc=None,
    )

    # seleção do intervalo de anos
    years_range = years_range or get_years_range()
    years_as_str = str_years_list(years_range)

    # obtém dataset selecionando artigos do Brasil, Acesso Aberto (AA),
    # intervalo de anos, parâmetros de contexto
    dataset = ScholarlyArticles.objects.filter(
        Q(contributors__affiliation__official__location__country__acron2='BR') |
        Q(contributors__affiliation__country__acron2='BR'),
        open_access_status__in=OA_STATUS_ITEMS,
        year__in=years_as_str,
        **context_params,
    )
    indicator = create_record(
        title=_get_scientific_production_indicator_title(
            category_title, context_id, keywords, years_range),
        action=action,
        classification=classification,
        practice=practice,
        scope=scope,
        measurement=measurement,
        creator_id=creator_id,
        scientific_production=scientific_production,
        start_date_year=years_range[0] if years_range else None,
        end_date_year=years_range[-1] if years_range else None,
        keywords=keywords
    )
    indicator.save_raw_data(dataset.iterator())

    args = []
    args.extend(category_attributes)
    # args.extend(context_params.keys())
    summarized = dataset.values(
                'year',
                *args,
            ).annotate(
                count=Count('id'),
            ).iterator()
    indicator.summarized = {
        'items': list(_add_category_name(
            summarized, category_attributes, category_name, ['year'], 'year')),
        'cat1_name': category_name,
        'cat2_name': 'year',
        'cat2_values': years_as_str,
    }
    indicator.save_raw_data(dataset.iterator())
    logging.info(keywords)
    # indicator.description = " | ".join(keywords)
    indicator.creator_id = creator_id
    indicator.save()


def _get_scientific_production_indicator_title(category_title,
                                               context_id,
                                               keywords,
                                               years_range):
    context = " - " + _('Brasil')
    if context_id:
        context = f" {CONTEXTS[context_id]['preposition']} {', '.join(keywords)}"

    return (
        'Evolução do número de artigos em acesso aberto por {} - {}-{} {}'.format(
            category_title,
            years_range[0], years_range[-1],
            context,
        )
    )
