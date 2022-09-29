import csv
import io
import json

from django.db.models import Count
from django.utils.translation import gettext as _

from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory

from .models import Indicator, Results, Versioning
from . import choices


# def generate_indicator(
#         practice, action, classification,
#         institution,
#         thematic_area,
#         start_date, end_date,
#         location,
#         return_data=True,
#         return_rows=True,
#         ):
#     """
#     Generate indicator according to the provided parameters

#     Parameters
#     ----------
#     practice : Practice
#     action : Action
#     classification: str
#     institution : Institution
#     thematic_area : ThematicArea
#     start_date : DateField
#     end_date : DateField
#     location : Location
#     return_data : boolean
#     return_rows : boolean

#     Returns
#     -------
#     Indicator

#     """
#     # gera nome do indicador
#     name = generate_indicator_title(
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date, end_date,
#         location,
#     )
#     # cria uma instância de Indicator
#     indicator = create_indicator(name)

#     # atualiza a instância indicator com o resultado
#     add_indicator_results(
#         indicator,
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date, end_date,
#         location,
#         return_data,
#         return_rows,
#         )

#     # TODO atualizar link e source
#     # indicator.link = ''
#     # indicator.source = ''

#     # retorna a instância de Indicator
#     # nota que não está salvo
#     return indicator


# def add_indicator_results(
#         indicator,
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date,
#         end_date,
#         location,
#         return_data,
#         return_rows,

#         ):
#     """
#     Adiciona os resultados na instância de Indicator

#     Parameters
#     ----------
#     indicator : Indicator
#     practice : Practice
#     action : Action
#     classification: str
#     institution : Institution
#     thematic_area : ThematicArea
#     start_date : DateField
#     end_date : DateField
#     location : Location
#     return_data : boolean
#     return_rows : boolean

#     Returns
#     -------
#     Indicator
#     """
#     if return_rows:
#         rows = []
#     if return_data:
#         json_data = []
#     indicator.results = Results()
#     indicator.results.save()
#     attributes = (
#         indicator.results.education_results,
#         indicator.results.event_results,
#         indicator.results.infrastructure_results,
#         indicator.results.policy_results,
#     )
#     models = (EducationDirectory, EventDirectory, InfrastructureDirectory,
#               PolicyDirectory)
#     for index, model in enumerate(models):
#         result = get_model_results(
#             model,
#             practice,
#             action,
#             classification,
#             institution,
#             thematic_area,
#             start_date,
#             end_date,
#             location,
#             return_data=return_data,
#             return_rows=return_rows,
#             )
#         attributes[index] = result['items']
#         if return_rows:
#             rows.extend(result['rows'])
#         if return_data:
#             json_data.extend(result['data'])

#     if return_rows:
#         csv_file = io.StringIO()
#         csv.writer(csv_file).writerows(rows)
#         indicator.file_csv = csv_file

#     if return_data:
#         json_data = json.dumps(rows, indent=4)
#         indicator.file_json = json_data

#     indicator.results.save()


# def generate_indicator_title(
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date=None,
#         end_date=None,
#         location=None,
#         ):
#     """
#     Generate indicator according to the provided parameters

#     Parameters
#     ----------
#     practice : Practice
#     action : Action
#     classification: str
#     institution : Institution
#     thematic_area : ThematicArea
#     start_date : DateField
#     end_date : DateField
#     location : Location

#     Returns
#     -------
#     str
#     """
#     args = (
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date,
#         end_date,
#         location,
#     )

#     #Considerando que um indicador é composto exatamente por dois args
#     name = "Número de "
#     for attrib in args:
#         if attrib:
#             name += attrib

#     return _(name)


def create_indicator(
        action,
        classification,
        practice,
        scope):
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
    """
    try:
        previous = Indicator.objects.filter(
            action=action,
            practice=practice,
            classification=classification,
            scope=scope,
            versioning__posterior_record=None)[0]
        seq = previous.seq + 1
        previous.validity = choices.OUTDATED
    except IndexError:
        seq = 1
        previous = None

    versioning = Versioning()
    versioning.seq = seq
    versioning.previous_record = previous
    versioning.posterior_record = None
    versioning.save()

    indicator = Indicator()
    indicator.title = title
    indicator.versioning = versioning
    indicator.validity = choices.CURRENT
    indicator.action = action
    indicator.practice = practice
    indicator.classification = classification
    indicator.scope = scope

    if previous:
        versioning.posterior_record = indicator
        previous.versioning = versioning
        previous.save()

    indicator.record_status = choices.PUBLISHED
    return indicator


# def get_model_results(
#         model,
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date=None,
#         end_date=None,
#         location=None,
#         return_data=False,
#         return_rows=False,
#         ):
#     """
#     Generate indicator according to the provided parameters

#     Parameters
#     ----------
#     model : model.Model (*Directory)
#     practice : Practice
#     action : Action
#     classification: str
#     institution : Institution
#     thematic_area : ThematicArea
#     start_date : DateField
#     end_date : DateField
#     location : Location
#     return_data : boolean
#     return_rows : boolean

#     Returns
#     -------
#     dict
#         keys:
#             params : queryset
#             data : list of dict (like json)
#             rows : list of dict (like jsonl)
#             items : query result
#             count : total of items
#     """

#     kwargs = get_kwargs(
#         model,
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date,
#         end_date,
#         location,
#     )
#     result = get_result(model, kwargs,
#                         return_data=return_data, return_rows=return_rows)
#     result['params'] = kwargs

#     return result


# def get_kwargs(
#         model,
#         practice,
#         action,
#         classification,
#         institution,
#         thematic_area,
#         start_date=None,
#         end_date=None,
#         location=None,
#         ):
#     """
#     Obtém os parâmetros para a consulta

#     Parameters
#     ----------
#     model : model.Model (*Directory)
#     practice : Practice
#     action : Action
#     classification: str
#     institution : Institution
#     thematic_area : ThematicArea
#     start_date : DateField
#     end_date : DateField
#     location : Location

#     Returns
#     -------
#     dict
#         keys:
#             practice
#             action
#             classification
#             institutions (se aplicável)
#             organization (se aplicável)
#             thematic_areas
#             start_date (se aplicável)
#             end_date (se aplicável)
#             date (se aplicável)
#             locations (se aplicável)
#     """
#     items = (
#         {'attribute': 'practice', 'value': practice},
#         {'attribute': 'action', 'value': action},
#         {'attribute': 'classification', 'value': classification},
#         {'attribute': 'institutions', 'value': institution},
#         {'attribute': 'organization', 'value': institution},
#         {'attribute': 'thematic_areas', 'value': thematic_area},
#         {'attribute': 'start_date', 'value': start_date},
#         {'attribute': 'end_date', 'value': end_date},
#         {'attribute': 'date', 'value': start_date},
#         {'attribute': 'locations', 'value': location},
#     )
#     kwargs = {}
#     for item in items:
#         if hasattr(model, item['attribute']) and item['value']:
#             kwargs[item['attribute']] = item['value']
#     return kwargs


# def get_result(model, kwargs, return_data=False, return_rows=False):
#     """
#     Faz a consulta e retorna os resultados

#     Parameters
#     ----------
#     model : model.Model (*Directory)
#     kwargs : parametros para a consulta
#     return_data : boolean
#         True para retornar resultado em formato "json"
#     return_rows : boolean
#         True para retornar resultado em formato "jsonl"

#     Returns
#     -------
#     dict
#         keys:
#             data : list of dict (like json)
#             rows : list of dict (like jsonl)
#             items : query result
#             count : total of items
#     """
#     items = model.objects.filter(**kwargs)
#     result = {
#         "items": items,
#         "count": items.count(),
#     }
#     if return_data:
#         result['data'] = list(format_query_result_as_json(items))
#     if return_rows:
#         result['rows'] = list(format_query_result_as_rows(items))

#     return result


# def format_query_result_as_json(items):
#     """
#     Formata o resultado da consulta como "json"

#     Parameters
#     ----------
#     items : resultado da consulta

#     Returns
#     -------
#     generator de items formatado como "json"
#     """
#     for item in items:
#         data = {}
#         add_practice(data, item)
#         add_action(data, item)
#         add_classification(data, item)
#         add_institutions(data, item)
#         add_locations(data, item)
#         add_thematic_areas(data, item)
#         add_dates(data, item)
#         yield data


# def add_practice(data, item):
#     try:
#         data['practice'] = item.practice.name
#     except AttributeError:
#         pass


# def add_action(data, item):
#     try:
#         data['action'] = item.action.name
#     except AttributeError:
#         pass


# def add_classification(data, item):
#     try:
#         data['classification'] = item.classification
#     except AttributeError:
#         pass


# def add_institutions(data, item):
#     try:
#         data['institutions'] = list(get_institutions_data(item.institutions))
#     except AttributeError:
#         pass


# def add_locations(data, item):
#     try:
#         data['locations'] = list(get_locations_data(item.location))
#     except AttributeError:
#         pass


# def add_thematic_areas(data, item):
#     try:
#         data['thematic_areas'] = list(
#             get_thematic_areas_data(item.thematic_areas))
#     except AttributeError:
#         pass


# def add_dates(data, item):
#     # TODO formatar a data para ser serializável
#     try:
#         data['start_date'] = item.date
#         data['end_date'] = item.date
#         return
#     except AttributeError:
#         pass

#     try:
#         data['start_date'] = item.start_date
#         data['end_date'] = item.end_date
#         return
#     except AttributeError:
#         pass


# def get_thematic_areas_data(thematic_areas):
#     for thematic_area in thematic_areas:
#         yield {
#             "level0": thematic_area.level0,
#             "level1": thematic_area.level1,
#             "level2": thematic_area.level2,
#         }


# def get_institutions_data(institutions):
#     for institution in institutions:
#         yield {
#             "name": institution.name,
#             "acronym": institution.acronym,
#             "location": {
#                 "city": institution.location.city,
#                 "state": institution.location.state,
#                 "region": institution.location.region,
#                 "country": institution.location.country,
#             },
#         }


# def get_locations_data(locations):
#     for location in locations:
#         yield {
#             "city": location.city,
#             "state": location.state,
#             "region": location.region,
#             "country": location.country,
#         }


# def format_query_result_as_rows(items):
#     """
#     Formata o resultado da consulta como "jsonl"

#     Parameters
#     ----------
#     items : resultado da consulta

#     Returns
#     -------
#     generator de items formatado como "jsonl"
#     """
#     for item in items:
#         data = {}
#         add_practice(data, item)
#         add_action(data, item)
#         add_classification(data, item)
#         add_dates(data, item)

#         for institution in item.institutions:
#             row_institution = get_institution_row(institution)

#             for location in item.locations:
#                 row_location = get_location_row(location)
#                 for thematic_area in item.thematic_areas:
#                     row = {}
#                     row.update(data)
#                     row.update(row_institution)
#                     row.update(row_location)
#                     row.update(get_thematic_area_row(thematic_area))

#                     yield row


# def get_thematic_area_row(thematic_area):
#     row = {}
#     row["thematic_area_level0"] = thematic_area.level0
#     row["thematic_area_level1"] = thematic_area.level1
#     row["thematic_area_level2"] = thematic_area.level2
#     return row


# def get_institution_row(institution):
#     row = {}
#     row['institution_name'] = institution.name
#     row['institution_acronym'] = institution.acronym
#     row['institution_city'] = institution.location.city
#     row['institution_state'] = institution.location.state
#     row['institution_region'] = institution.location.region
#     row['institution_country'] = institution.location.country
#     return row


# def get_location_row(location):
#     row = {}
#     row["city"] = location.city
#     row["state"] = location.state
#     row["region"] = location.region
#     row["country"] = location.country
#     return row


# def generate_indicator_in_institutional_context(title, action, creator_id):
#     """
#     Generate indicator according to the provided parameters

#     Parameters
#     ----------
#     title : str
#     action : Action

#     Returns
#     -------
#     Indicator

#     """
#     # cria uma instância de Indicator
#     indicator = create_indicator(title)

#     indicator.results = Results()
#     indicator.results.save()

#     rows = {}

#     results = get_actions_in_model(
#         action, EducationDirectory, 'institutions')
#     indicator.results.education_results = results['items']
#     rows['education'] = results['rows']

#     results = get_actions_in_model(
#         action, EventDirectory, 'organization', 'institutions')
#     indicator.results.event_results = results['items']
#     rows['event'] = results['rows']

#     results = get_actions_in_model(
#         action, InfrastructureDirectory, 'institutions')
#     indicator.results.infrastructure_results = results['items']
#     rows['infrastructure'] = results['rows']

#     results = get_actions_in_model(
#         action, PolicyDirectory, 'institutions')
#     indicator.results.policy_results = results['items']
#     rows['policy'] = results['rows']
#     indicator.results.save()

#     csv_file = io.StringIO()
#     writer = csv.writer(csv_file)
#     for rows_ in rows.values():
#         writer.writerows(rows_)
#     indicator.file_csv = csv_file

#     # json_data = json.dumps(rows, indent=4)
#     # indicator.file_json = json.dumps(rows, indent=4)

#     # TODO atualizar link e source
#     # indicator.link = ''
#     # indicator.source = ''

#     # retorna a instância de Indicator
#     indicator.creator_id = creator_id

#     indicator.save()
#     return indicator


# def get_actions_in_model(action, model, context_attribute, standardized_name=None):
#     """
#     >>> City.objects.values('country__name') \
#           .annotate(country_population=Sum('population')) \
#           .order_by('-country_population')
#     [
#       {'country__name': u'China', 'country_population': 309898600},
#       {'country__name': u'United States', 'country_population': 102537091},
#       {'country__name': u'India', 'country_population': 100350602},
#       {'country__name': u'Japan', 'country_population': 65372000},
#       {'country__name': u'Brazil', 'country_population': 38676123},
#       '...(remaining elements truncated)...'
#     ]
#     """
#     items = model.objects.filter(action=action)
#     return {
#         "items": items,
#         "rows": get_rows_grouped_by__classification_practice_institution(
#             items, context_attribute, standardized_name)
#     }


# def get_rows_grouped_by__classification_practice_institution(
#         items, context_attribute, standardized_name):

#     for item in items.values(
#                 'classification',
#                 'practice__name',
#                 context_attribute,
#             ).annotate(
#                 count=Count(context_attribute)
#             ).order_by('-count'):
#         if standardized_name:
#             item[standardized_name] = item.pop(context_attribute)
#         yield json.dumps(item)

#########################################################################


def generate_indicators_in_institutional_context(title, action, creator_id):
    """
    Generate indicator according to the provided parameters

    Parameters
    ----------
    title : str
    action : Action

    Returns
    -------
    Indicator

    """

    indicators_data = {}
    for classification_and_practice, results in get_results_grouped_by_action_classification_and_practice(
            action, EducationDirectory, 'institutions'):
        indicators_data.setdefault(classification_and_practice, {})
        indicators_data[classification_and_practice]['education'] = results

    for classification_and_practice, results in get_results_grouped_by_action_classification_and_practice(
            action, EventDirectory, 'organization', 'institutions'):
        indicators_data.setdefault(classification_and_practice, {})
        indicators_data[classification_and_practice]['event'] = results

    for classification_and_practice, results in get_results_grouped_by_action_classification_and_practice(
            action, InfrastructureDirectory, 'institutions'):
        indicators_data.setdefault(classification_and_practice, {})
        indicators_data[classification_and_practice]['infrastructure'] = results

    for classification_and_practice, results in get_results_grouped_by_action_classification_and_practice(
            action, PolicyDirectory, 'institutions'):
        indicators_data.setdefault(classification_and_practice, {})
        indicators_data[classification_and_practice]['policy'] = results

    # registra um indicador por categoria e pratica resultante
    # da junção de todos os resultados de todos os diretórios
    for classification_and_practice, results in indicators_data.items():

        text = f"{results['labels']['classification']} {results['labels']['practice__name']}"

        # cria o registro indicador
        create_indicator_action_classification_and_practice(
            action=action,
            title=title,
            data=results,
            creator_id=creator_id,
        )


def get_results_grouped_by_action_classification_and_practice(
        action, model, context_attribute, standardized_name=None):
    """
    Faz a consulta em um dado modelo (`model`) pela `action`
    """
    groups = {}
    for row in get_rows_grouped_by__classification_and_practice(model, action):
        key = (row['classification'], row['practice__code'])

        items = model.objects.filter(
            action=action,
            classification=row['classification'],
            practice_code=row['practice__code'],
        )

        groups.setdefault(key, {})
        groups[key] = {
            "labels": {
                "classification": row['classification'],
                "practice__code": row['practice__code'],
                "practice__name": row['practice__name'],
            },
            "items": items,
            "data": count_occurences_in_context(
                items, context_attribute, standardized_name),
        }
        groups
    return groups


def get_rows_grouped_by__classification_and_practice(model, action):
    """
    >>> City.objects.values('country__name') \
          .annotate(country_population=Sum('population')) \
          .order_by('-country_population')
    [
      {'country__name': u'China', 'country_population': 309898600},
      {'country__name': u'United States', 'country_population': 102537091},
      {'country__name': u'India', 'country_population': 100350602},
      {'country__name': u'Japan', 'country_population': 65372000},
      {'country__name': u'Brazil', 'country_population': 38676123},
      '...(remaining elements truncated)...'
    ]
    """
    return model.objects.filter(action=action).values(
        'classification',
        'practice__code',
        'practice__name',
    ).annotate(count=Count('id'))


def count_occurences_in_context(items, context_attribute, standardized_name):
    """
    Parameters
    ----------
    items : QuerySet
    context_attribute : str (ex.: 'organization')
    standardized_name : str (ex.: 'institutions')

    """

    # https://docs.djangoproject.com/en/4.1/ref/models/querysets/#values
    #
    # >>> from django.db.models import Count
    # >>> Blog.objects.values('entry__authors', entries=Count('entry'))
    # <QuerySet [{'entry__authors': 1, 'entries': 20}, {'entry__authors': 1, 'entries': 13}]>
    # >>> Blog.objects.values('entry__authors').annotate(entries=Count('entry'))
    # <QuerySet [{'entry__authors': 1, 'entries': 33}]>

    for item in items.values(
                context_attribute,
            ).annotate(
                count=Count(context_attribute)
            ).order_by('-count'):
        if standardized_name:
            item['category_label'] = standardized_name
            item['category_value'] = str(item.pop(context_attribute))
        yield json.dumps(item)


def create_indicator_action_classification_and_practice(action, title, data, creator_id):

    # cria uma instância de Indicator

    for item in data.values():
        labels = item['labels']
        break
    text = f"{labels['classification']} {labels['practice__name']}"
    title = title.replace("[QUALIFICATION_AND_PRACTICE]", text)

    practice = Practice.get(code=labels['practice__code'])

    indicator = create_indicator(
        action=action,
        classification=labels['classification'],
        practice=practice,
        scope=INSTITUTIONAL,
    )
    indicator.action = action
    indicator.classification = labels['classification']
    indicator.practice = practice

    csv_file = io.StringIO()
    writer = csv.writer(csv_file)
    for data_ in data.values():
        writer.writedata(data_['data'])
    indicator.file_csv = csv_file

    indicator.education_results = data['education']['items']
    indicator.event_results = data['event']['items']
    indicator.infrastructure_results = data['infrastructure']['items']
    indicator.policy_results = data['policy']['items']

    # json_data = json.dumps(rows, indent=4)
    # indicator.file_json = json.dumps(rows, indent=4)

    # TODO atualizar link e source
    # indicator.link = ''
    # indicator.source = ''

    # retorna a instância de Indicator
    indicator.creator_id = creator_id

    indicator.save()
    return indicator
