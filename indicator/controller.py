from random import randint
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

from django_celery_beat.models import PeriodicTask, CrontabSchedule

from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory

from scholarly_articles.models import ScholarlyArticles, Affiliations
from location.models import Location
from institution.models import Institution
from usefulmodels.models import Practice, State, Action, Country, ThematicArea
from .models import Indicator, ActionAndPractice
from . import choices


class GetOrCreateCrontabScheduleError(Exception):
    ...


class CreateIndicatorRecordError(Exception):
    ...


User = get_user_model()


OA_STATUS_ITEMS = ('gold', 'bronze', 'green', 'hybrid', )

CATEGORIES = {
    'OPEN_ACCESS_STATUS': {
        'title': 'categoria de acesso aberto',
        'name': 'categoria de acesso aberto',
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
            'thematic_areas__level1',
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
            'thematic_areas__level1',
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

##########################################################################
def schedule_evolution_of_scientific_production_tasks(
        creator_id,
        years_range,
        ):
    years_as_str = str_years_list(years_range)

    for category_id in ('OPEN_ACCESS_STATUS', 'USE_LICENSE', ):
        logging.info(category_id)
        try:
            _schedule_evolution_of_scientific_production_task(
                creator_id,
                category_id,
                list(years_range),
            )
        except Exception as e:
            logging.exception(e)
            continue

    for context_id in ("AFFILIATION_UF", "AFFILIATION"):
        logging.info(context_id)
        for context_params in _get_context_items(
                CONTEXTS[context_id]['category_attributes'], years_as_str):
            context_params.pop('count')
            for category_id in ('OPEN_ACCESS_STATUS', 'USE_LICENSE'):
                logging.info(context_params)
                try:
                    _schedule_evolution_of_scientific_production_task(
                        creator_id,
                        category_id,
                        list(years_range),
                        context_params,
                        context_id,
                    )
                except Exception as e:
                    logging.exception(e)
                    continue


def _schedule_evolution_of_scientific_production_task(
        creator_id,
        category_id,
        years_range,
        context_params=None,
        context_id=None,
        ):
    task = _("Geração de indicadores de artigos científicos em acesso aberto")
    context = list((context_params or {}).values())
    name = f'{category_id} | {context} | {years_range[0]}-{years_range[-1]}'
    kwargs = dict(
        creator_id=creator_id,
        category_id=category_id,
        initial_year=years_range[0],
        final_year=years_range[-1],
        context_params=context_params,
        context_id=context_id,
    )
    hours_after_now = 0
    minutes_after_now = randint(1, 30)
    priority = randint(1, 9)
    get_or_create_periodic_task(
        name, task, kwargs,
        hours_after_now, minutes_after_now, priority,
    )

##########################################################################
def schedule_directory_numbers_tasks(
        creator_id,
        ):
    for category2_id in (None, 'CA_PRACTICE', 'THEMATIC_AREA'):
        _schedule_directory_numbers_without_context_task(
            creator_id, category2_id)
    for context_id in ('THEMATIC_AREA', 'LOCATION', 'INSTITUTION', ):
        _schedule_directory_numbers_with_context_task(creator_id, context_id)


def _schedule_directory_numbers_without_context_task(
        creator_id,
        category2_id,
        ):
    task = _("Geração de indicadores de ações em Ciência Aberta sem contexto")
    name = _('Ações em CA {}').format(category2_id)
    kwargs = dict(
        creator_id=creator_id,
        category2_id=category2_id,
    )
    hours_after_now = 0
    minutes_after_now = randint(1, 5)
    priority = 1
    get_or_create_periodic_task(
        name, task, kwargs,
        hours_after_now, minutes_after_now, priority,
    )


def _schedule_directory_numbers_with_context_task(
        creator_id,
        context_id,
        ):
    task = _("Geração de indicadores de ações em Ciência Aberta com contexto")
    name = _('Ações em CA {}').format(context_id)
    kwargs = dict(
        creator_id=creator_id,
        context_id=context_id,
    )
    hours_after_now = 0
    minutes_after_now = randint(2, 10)
    priority = 1
    get_or_create_periodic_task(
        name, task, kwargs,
        hours_after_now, minutes_after_now, priority,
    )


##########################################################################
def sum_hours_and_minutes(hours_after_now, minutes_after_now, now=None):
    """
    Retorna a soma dos minutos / horas a partir da hora atual
    """
    now = now or datetime.utcnow()
    hours = now.hour + hours_after_now
    minutes = now.minute + minutes_after_now
    if minutes > 59:
        hours += 1
    hours = hours % 24
    minutes = minutes % 60
    return hours, minutes


def get_or_create_crontab_schedule(day_of_week=None, hour=None, minute=None):
    try:
        crontab_schedule, status = CrontabSchedule.objects.get_or_create(
            day_of_week=day_of_week or '*',
            hour=hour or '*',
            minute=minute or '*',
        )
    except Exception as e:
        raise GetOrCreateCrontabScheduleError(
            _('Unable to get_or_create_crontab_schedule {} {} {} {} {}').format(
                day_of_week, hour, minute, type(e), e
            )
        )
    return crontab_schedule


def get_or_create_periodic_task(
        name, task, kwargs,
        hours_after_now, minutes_after_now, priority,
        ):
    try:
        periodic_task = PeriodicTask.objects.get(name=name)
    except PeriodicTask.DoesNotExist:
        periodic_task = PeriodicTask()
        periodic_task.name = name
        periodic_task.task = task
        periodic_task.kwargs = json.dumps(kwargs)

    hours, minutes = sum_hours_and_minutes(
        hours_after_now, minutes_after_now)
    periodic_task.priority = priority
    periodic_task.enabled = True
    periodic_task.one_off = True
    periodic_task.crontab = get_or_create_crontab_schedule(
        hour=hours,
        minute=minutes,
    )
    periodic_task.save()
    logging.info(
        _('Scheduled %s %s %s %s') % (name, hours, minutes, priority))

##########################################################################

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

#########################################################################
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


def delete_tasks():
    for item in PeriodicTask.objects.filter(name__contains='indicadores').iterator():
        try:
            item.delete()
        except Exception as e:
            logging.exception(e)


#########################################################################

def _add_param(params, name, value):
    if value:
        params[name] = value
    else:
        params[f'{name}__isnull'] = True


def fix_params(params):
    args = {}
    for name, value in params.items():
        if value:
            args[name] = value
        else:
            args[f'{name}__isnull'] = True
    return args


def get_latest_version(code):
    """
    Obtém a versão mais recente de uma instância de Indicator,

    Parameters
    ----------
    code : str
    """
    try:
        return Indicator.objects.filter(
            code=code, posterior_record__isnull=True)[0]
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
        object_name,
        category_title=None,
        start_date_year=None,
        end_date_year=None,
        category1=None,
        category2=None,
        context=None,
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
    title = generate_title(
        measurement,
        object_name,
        start_date_year,
        end_date_year,
        category_title,
        context,
        )
    code = build_code(
        action,
        classification,
        practice,
        measurement,
        object_name,
        start_date_year,
        end_date_year,
        category1,
        category2,
        context,
    )
    latest = get_latest_version(code)
    if latest:
        if latest.record_status == choices.WIP:
            raise CreateIndicatorRecordError(
                "There is already a new record being created {} {} {}".format(
                    latest.code, latest.seq, latest.created
                )
            )
        seq = latest.seq + 1
        action_and_practice = latest.action_and_practice
    else:
        seq = 1
        if any([action, classification, practice]):
            action_and_practice = ActionAndPractice.get_or_create(
                action, classification, practice
            )
        else:
            action_and_practice = None

    logging.info("Create Indicator")
    indicator = Indicator()
    indicator.code = code
    indicator.seq = seq
    indicator.record_status = choices.WIP
    if latest:
        indicator.previous_record = latest
    indicator.posterior_record = None
    indicator.title = title
    indicator.validity = choices.CURRENT
    indicator.action_and_practice = action_and_practice
    indicator.scope = scope
    indicator.measurement = measurement
    indicator.object_name = object_name
    indicator.category = category_title
    indicator.context = " | ".join(context)
    indicator.start_date_year = start_date_year
    indicator.end_date_year = end_date_year
    indicator.creator_id = creator_id
    indicator.save()
    logging.info("Created {} {} {}".format(code, seq, indicator.record_status))
    return indicator


def build_code(
        action,
        classification,
        practice,
        measurement,
        object_name,
        start_date_year,
        end_date_year,
        category1,
        category2,
        context,
        ):
    items = [
        action and action.code,
        classification,
        practice and practice.code,
        measurement,
        object_name,
        str(start_date_year or ''),
        str(end_date_year or ''),
    ] + (category1 or []) + (category2 or []) + (context or [])

    return "_".join([item.replace(" ", "_") or '' for item in items if item]).upper()


def generate_title(
        measurement,
        object_name,
        start_date_year=None,
        end_date_year=None,
        category=None,
        context=None,
        ):
    parts = []
    if start_date_year and end_date_year:
        parts += ['Evolução do número de']
    if measurement == choices.FREQUENCY:
        parts += ['Número de']
    parts += [object_name]
    if category:
        parts += [f"por {category}"]
    if start_date_year and end_date_year:
        parts += [f'- {start_date_year}-{end_date_year}']
    parts += (context or [_('no Brasil')])
    return " ".join(parts)


def save_indicator(indicator, keywords=None):
    # indicator.creator_id = creator_id
    indicator.record_status = choices.PUBLISHED
    indicator.save()

    if keywords:
        indicator.keywords.add(*keywords)
        indicator.save()

    if indicator.previous_record:
        indicator.previous_record.posterior_record = indicator
        indicator.previous_record.validity = choices.OUTDATED
        indicator.previous_record.save()
    logging.info("Created {} {} {}".format(indicator.code, indicator.seq, indicator.record_status))


##############################################################################
def generate_directory_numbers_without_context(
        creator_id,
        category2_id=None,
        ):

    preposition = _("Brasil")

    category_id = "CA_ACTION"
    cat1 = CATEGORIES[category_id]
    cat1_title = cat1['title']
    cat1_name = cat1['name']
    cat1_attrs = cat1['category_attributes']
    cat1_attrs_options = cat1.get('category_attributes_options')
    cats_attrs = cat1_attrs.copy()

    cat2_attrs = None
    if category2_id:
        cat2 = CATEGORIES[category2_id]
        cat2_title = cat2['title']
        cat2_name = cat2['name']
        cat2_attrs = cat2['category_attributes']
        cat2_attrs_options = cat2.get('category_attributes_options')
        cats_attrs += cat2_attrs

    scope = choices.GENERAL
    measurement = choices.FREQUENCY

    items = []
    items.extend(_directory_numbers(EducationDirectory.objects, cats_attrs))
    items.extend(_directory_numbers(EventDirectory.objects, cats_attrs))
    items.extend(_directory_numbers(InfrastructureDirectory.objects, cats_attrs))
    items.extend(_directory_numbers(PolicyDirectory.objects, cats_attrs))
    keywords = [_('Brasil')]
    indicator = create_record(
        title='',
        action=None,
        classification=None,
        practice=None,
        scope=scope,
        measurement=measurement,
        creator_id=creator_id,
        object_name=_('ações em Ciência Aberta'),
        category_title=category2_id and CATEGORIES[category2_id]['title'],
        category1=cat1_attrs,
        category2=cat2_attrs,
        context=keywords,
    )
    if category2_id:
        # cat1 = variável cujo valor é comum nos registros
        # por ex, year, practice__name
        indicator.summarized = {
            'items': list(_add_category_name(
                items,
                cat1_attrs, cat1_name,
                cat2_attrs, cat2_name)),
            'cat1_name': cat1_name,
            'cat2_name': cat2_name,
        }
    else:
        indicator.summarized = {
            "items": list(
                _add_category_name(
                    items, cat1_attrs, cat1_name)),
            "cat1_name": cat1_name,
        }
    # indicator.total = len(items)
    save_indicator(indicator, keywords)
    indicator.save_raw_data(
        list(EducationDirectory.objects.iterator()) +
        list(EventDirectory.objects.iterator()) +
        list(InfrastructureDirectory.objects.iterator()) +
        list(PolicyDirectory.objects.iterator())
    )

###############################################################################
def generate_directory_numbers_with_context(
        creator_id,
        context_id,
        ):
    # obtém contexto de todos os diretórios
    for group, directories_and_contexts in _get_directories_contexts(context_id).items():
        for category2_id in ('CA_PRACTICE', 'THEMATIC_AREA'):
            if category2_id != context_id:
                _generate_directory_numbers_for_category(
                    directories_and_contexts,
                    context_id,
                    category2_id,
                )


def _generate_directory_numbers_for_category(
        directories_and_contexts,
        context_id,
        category2_id,
        ):

    category_id = "CA_ACTION"

    logging.info((category_id, category2_id, context_id))

    cat2_attrs = None

    cat1 = CATEGORIES[category_id]
    title = "Número de {} em Ciência Aberta".format(cat1['title'])
    cat1_attrs = cat1['category_attributes']
    cats_attributes = cat1_attrs.copy()

    if category2_id:
        cat2 = CATEGORIES[category2_id]
        title = "Número de {} em Ciência Aberta por {}".format(
            cat1['title'], cat2['title'])
        cat2_attrs = cat2['category_attributes']
        cats_attributes += cat2_attrs

    datasets, items, keywords = _get_directory__dataset_and_items_and_keywords(
        directories_and_contexts,
        cats_attributes,
    )
    logging.info((len(datasets), len(items), len(keywords)))
    if not datasets:
        logging.info("Not found directory records for {}".format(
            directories_and_contexts))
        return

    # tenta criar indicador
    scope = choices.GENERAL
    measurement = choices.FREQUENCY

    try:
        indicator = create_record(
            title='',
            action=None, classification=None, practice=None,
            scope=scope, measurement=measurement, creator_id=creator_id,
            object_name=_('ações em Ciência Aberta'),
            category_title=category2_id and CATEGORIES[category2_id]['title'],
            category1=cat1_attrs,
            category2=cat2_attrs,
            context=keywords,
        )
    except CreateIndicatorRecordError:
        # já está em progresso de criação
        return

    if category2_id:
        # cat2: variável em comum nos diretórios
        # por ex: year, practice__name
        indicator.summarized = {
            'items': list(_add_category_name(
                items,
                cat1_attrs, cat1['name'],
                cat2_attrs, cat2['name'],
                )),
            'cat1_name': cat1['name'],
            'cat2_name': cat2['name'],
        }
    else:
        indicator.summarized = {
            'items': list(_add_category_name(
                items,
                cat1_attrs, cat1['name'],
                )),
            'cat1_name': cat1['name'],
        }
    # indicator.total = len(items)
    _add_context(indicator, context_id, context_params)
    save_indicator(indicator, keywords)
    indicator.save_raw_data(datasets_iterator(datasets))


###########################################################################

def _get_directories_contexts(context_id):
    """
    Obtém os dados dos contextos (lista de instituições ou UF ou áreas temáticas)
    coletados de todos os diretórios
    """
    contexts = {}
    for model in (EducationDirectory, EventDirectory, InfrastructureDirectory, PolicyDirectory):
        for context_item in _directory_context_items(model, context_id):
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


def _get_directory__dataset_and_items_and_keywords(
        directories_context,
        cat_attributes,
        ):

    datasets = []
    items = []
    keywords = []

    # para cada diretório, obtém seus ítens contextualizados
    for directory, dir_ctxt_params in directories_context:
        logging.info((directory, dir_ctxt_params))

        if not all(dir_ctxt_params.values()):
            continue

        if not keywords:
            keywords.extend([v for v in dir_ctxt_params.values() if v])
        logging.info(keywords)
        # obtém de um diretório, seu dataset contextualizado
        filters = {}
        for name, value in dir_ctxt_params.items():
            _add_param(filters, name, value)
        dataset = directory.objects.filter(**filters)

        # adiciona o dataset do diretório no conjunto de datasets do contexto
        datasets.append(dataset)

        # adiciona os ítens sumarizados no conjuntos de ítens do contexto
        items.extend(_directory_numbers(dataset, cat_attributes))
    return (datasets, items, keywords)


def datasets_iterator(datasets):
    for dataset in datasets:
        yield from dataset.iterator()


def _directory_context_items(directory, context_id):
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
            for item in directory.objects.values(
                        *category_attributes_option
                    ).annotate(
                        count=Count('id', distinct=True)
                    ).order_by('count').iterator():
                item.pop('count')
                yield item
        except FieldError:
            continue

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

    indicator = create_record(
        title='',
        action=action,
        classification=classification,
        practice=practice,
        scope=choices.GENERAL,
        measurement=choices.FREQUENCY,
        creator_id=creator_id,
        object_name=_('periódicos em acesso aberto'),
        category_title=CATEGORIES[category_id]['title'],
        start_date_year=datetime.now().year,
    )

    dataset, summarized = _journals_numbers(category_attributes)
    indicator.summarized = {
        "items": list(_add_category_name(
                summarized, category_attributes)),
    }
    # indicator.total = len(indicator.summarized['items'])
    save_indicator(indicator)
    indicator.save_raw_data(dataset.iterator())


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
        try:
            evolution_of_scientific_production(
                creator_id,
                category_id,
                years_range,
                context_params,
                context_id,
            )
        except CreateIndicatorRecordError:
            continue


def _get_context_items(context_params, years_as_str):
    logging.info("_get_context_items %s %s" % (context_params, years_as_str))
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
        title='',
        action=action,
        classification=classification,
        practice=practice,
        scope=scope,
        measurement=measurement,
        creator_id=creator_id,
        object_name=_('artigos científicos em acesso aberto'),
        category_title=CATEGORIES[category_id]['title'],
        start_date_year=years_range[0] if years_range else None,
        end_date_year=years_range[-1] if years_range else None,
        category1=category_attributes,
        context=keywords,
    )
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
    _add_context(indicator, context_id, context_params)
    save_indicator(indicator, keywords=keywords)
    indicator.save_raw_data(dataset.iterator())


def _add_context(indicator, context_id, context_params):
    logging.info("Adding context %s %s %s" % (indicator, context_id, context_params))
    if context_id in ('AFFILIATION', 'INSTITUTION'):
        try:
            name = (
                context_params.get('contributors__affiliation__official__name') or
                context_params.get("institutions__name") or
                context_params.get("organization__name")
            )
            location__state__name = (
                context_params.get('contributors__affiliation__official__location__state__name') or
                context_params.get("institutions__location__state__name") or
                context_params.get("organization__location__state__name")
            )
            logging.info("Adding context %s %s" % (name, location__state__name))
            inst = Institution.objects.get(
                **fix_params(
                    dict(
                        name=name,
                        location__state__name=location__state__name,
                    )
                )
            )
        except Institution.DoesNotExist:
            logging.info("Adding context DoesNotExist")
        except Institution.MultipleObjectsReturned:
            logging.info("Adding context MultipleObjectsReturned")
        else:
            indicator.institutions.add(inst)
    elif context_id in ('AFFILIATION_UF', 'LOCATION'):
        try:
            state__name = (
                context_params.get(
                    'contributors__affiliation__official__location__state__name') or
                context_params.get(
                    'institutions__location__state__name') or
                context_params.get(
                    'organization__location__state__name') or
                context_params.get(
                    'locations__state__name')
            )
            state__acronym = (
                context_params.get(
                    'contributors__affiliation__official__location__state__acronym') or
                context_params.get(
                    'institutions__location__state__acronym') or
                context_params.get(
                    'organization__location__state__acronym') or
                context_params.get(
                    'locations__state__acronym')
            )
            logging.info("Adding context %s %s" % (state__name, state__acronym))

            args = fix_params(
                dict(
                    state__name=state__name,
                    state__acronym=state__acronym,
                )
            )

            location = Location.get_or_create_state(
                indicator.creator_id,
                **args,
            )
        except Location.DoesNotExist:
            logging.info("Adding context DoesNotExist")
        except Location.MultipleObjectsReturned:
            logging.info("Adding context MultipleObjectsReturned")
        else:
            indicator.locations.add(location)
    elif context_id in ('THEMATIC_AREA', ):
            thematic_areas__level1 = (
                context_params.get(
                    'thematic_areas__level1')
            )
            logging.info("Adding context %s" % (thematic_areas__level1, ))
            if thematic_areas__level1:
                for item in ThematicArea.objects.filter(
                        level1=thematic_areas__level1).iterator():
                    indicator.thematic_areas.add(item)
    else:
        return
