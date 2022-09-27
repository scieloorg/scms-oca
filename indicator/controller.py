from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory

from .models import Indicator, Results
from .choices import CURRENT, DEACTIVATED


def generate_indicator(
        practice, action, classification,
        institution,
        thematic_area,
        start_date, end_date,
        location,
        return_data=True,
        return_rows=True,
        ):
    """
    Generate indicator according to the provided parameters

    Parameters
    ----------
    practice : Practice
    action : Action
    classification: str
    institution : Institution
    thematic_area : ThematicArea
    start_date : DateField
    end_date : DateField
    location : Location
    return_data : boolean
    return_rows : boolean

    Returns
    -------
    Indicator

    """
    # gera nome do indicador
    name = generate_indicator_title(
        practice,
        action,
        classification,
        institution,
        thematic_area,
        start_date, end_date,
        location,
        return_data,
        return_rows,
    )
    # cria uma instância de Indicator
    indicator = create_indicator(name)

    # atualiza a instância indicator com o resultado
    add_indicator_results(
        indicator,
        practice,
        action,
        classification,
        institution,
        thematic_area,
        start_date, end_date,
        location,
        return_data,
        return_rows,
        )

    # TODO atualizar link e source
    # indicator.link = ''
    # indicator.source = ''

    # retorna a instância de Indicator
    # nota que não está salvo
    return indicator


def add_indicator_results(
        indicator,
        practice,
        action,
        classification,
        institution,
        thematic_area,
        start_date,
        end_date,
        location,
        return_data,
        return_rows,

        ):
    """
    Adiciona os resultados na instância de Indicator

    Parameters
    ----------
    indicator : Indicator
    practice : Practice
    action : Action
    classification: str
    institution : Institution
    thematic_area : ThematicArea
    start_date : DateField
    end_date : DateField
    location : Location
    return_data : boolean
    return_rows : boolean

    Returns
    -------
    Indicator
    """
    if return_rows:
        rows = []
    if return_data:
        json_data = []
    indicator.results = Results()
    attributes = (
        indicator.results.education_results,
        indicator.results.event_results,
        indicator.results.infrastructure_results,
        indicator.results.policy_results,
    )
    models = (EducationDirectory, EventDirectory, InfrastructureDirectory,
              PolicyDirectory)
    for index, model in enumerate(models):
        result = get_model_indicator(
            model,
            practice,
            action,
            classification,
            institution,
            thematic_area,
            start_date,
            end_date,
            location,
            return_data=return_data,
            return_rows=return_rows,
            )
        attributes[index] = result['items']
        if return_rows:
            rows.extend(result['rows'])
        if return_data:
            json_data.extend(result['data'])
    # FIXME gerar arquivo com conteúdo rows
    indicator.file_csv = rows
    # FIXME gerar arquivo com conteúdo json_data
    indicator.file_json = json_data


def generate_indicator_title(
        practice,
        action,
        classification,
        institution,
        thematic_area,
        start_date=None,
        end_date=None,
        location=None,
        ):
    """
    Generate indicator according to the provided parameters

    Parameters
    ----------
    practice : Practice
    action : Action
    classification: str
    institution : Institution
    thematic_area : ThematicArea
    start_date : DateField
    end_date : DateField
    location : Location

    Returns
    -------
    str
    """
    # TODO
    return _('Número ...')


def create_indicator(title):
    """
    Cria uma nova instância de Indicator,
    adicionando / atualizando os atributos `seq` e outros relacionados com
    a versão do indicador

    """
    try:
        previous = Indicator.objects.filter(
            title=title, versioning__posterior_record=None)[0]
        seq = previous.seq + 1
        previous.record_status = DEACTIVATED
    except IndexError:
        seq = 1
        previous = None

    indicator = Indicator()
    indicator.title = title
    indicator.versioning.seq = seq
    indicator.versioning.previous_record = previous
    indicator.record_status = CURRENT
    indicator.save()

    if previous:
        previous.versioning.posterior_record = indicator
        previous.save()

    return indicator


def get_model_indicator(
        model,
        practice,
        action,
        classification,
        institution,
        thematic_area,
        start_date=None,
        end_date=None,
        location=None,
        return_data=False,
        return_rows=False,
        ):
    """
    Generate indicator according to the provided parameters

    Parameters
    ----------
    model : model.Model (*Directory)
    practice : Practice
    action : Action
    classification: str
    institution : Institution
    thematic_area : ThematicArea
    start_date : DateField
    end_date : DateField
    location : Location
    return_data : boolean
    return_rows : boolean

    Returns
    -------
    dict
        keys:
            params : queryset
            data : list of dict (like json)
            rows : list of dict (like jsonl)
            items : query result
            count : total of items
    """

    kwargs = get_kwargs(
        model,
        practice,
        action,
        classification,
        institution,
        thematic_area,
        start_date,
        end_date,
        location,
    )
    result = get_result(model, kwargs,
                        return_data=return_data, return_rows=return_rows)
    result['params'] = kwargs

    return result


def get_kwargs(
        model,
        practice,
        action,
        classification,
        institution,
        thematic_area,
        start_date=None,
        end_date=None,
        location=None,
        ):
    """
    Obtém os parâmetros para a consulta

    Parameters
    ----------
    model : model.Model (*Directory)
    practice : Practice
    action : Action
    classification: str
    institution : Institution
    thematic_area : ThematicArea
    start_date : DateField
    end_date : DateField
    location : Location

    Returns
    -------
    dict
        keys:
            practice
            action
            classification
            institutions (se aplicável)
            organization (se aplicável)
            thematic_areas
            start_date (se aplicável)
            end_date (se aplicável)
            date (se aplicável)
            locations (se aplicável)
    """
    items = (
        {'attribute': 'practice', 'value': practice},
        {'attribute': 'action', 'value': action},
        {'attribute': 'classification', 'value': classification},
        {'attribute': 'institutions', 'value': institution},
        {'attribute': 'organization', 'value': institution},
        {'attribute': 'thematic_areas', 'value': thematic_area},
        {'attribute': 'start_date', 'value': start_date},
        {'attribute': 'end_date', 'value': end_date},
        {'attribute': 'date', 'value': start_date},
        {'attribute': 'locations', 'value': location},
    )
    kwargs = {}
    for item in items:
        if hasattr(model, item['attribute']):
            kwargs[item['attribute']] = item['value']
    return kwargs


def get_result(model, kwargs, return_data=False, return_rows=False):
    """
    Faz a consulta e retorna os resultados

    Parameters
    ----------
    model : model.Model (*Directory)
    kwargs : parametros para a consulta
    return_data : boolean
        True para retornar resultado em formato "json"
    return_rows : boolean
        True para retornar resultado em formato "jsonl"

    Returns
    -------
    dict
        keys:
            data : list of dict (like json)
            rows : list of dict (like jsonl)
            items : query result
            count : total of items
    """
    items = model.objects.filter(**kwargs)
    result = {
        "items": items,
        "count": items.count(),
    }
    if return_data:
        result['data'] = list(format_query_result_as_json(items))
    if return_rows:
        result['rows'] = list(format_query_result_as_rows(items))

    return result


def format_query_result_as_json(items):
    """
    Formata o resultado da consulta como "json"

    Parameters
    ----------
    items : resultado da consulta

    Returns
    -------
    generator de items formatado como "json"
    """
    for item in items:
        data = {}
        add_practice(data, item)
        add_action(data, item)
        add_classification(data, item)
        add_institutions(data, item)
        add_locations(data, item)
        add_thematic_areas(data, item)
        add_dates(data, item)
        yield data


def add_practice(data, item):
    try:
        data['practice'] = item.practice.name
    except AttributeError:
        pass


def add_action(data, item):
    try:
        data['action'] = item.action.name
    except AttributeError:
        pass


def add_classification(data, item):
    try:
        data['classification'] = item.classification
    except AttributeError:
        pass


def add_institutions(data, item):
    try:
        data['institutions'] = list(get_institutions_data(item.institutions))
    except AttributeError:
        pass


def add_locations(data, item):
    try:
        data['locations'] = list(get_locations_data(item.location))
    except AttributeError:
        pass


def add_thematic_areas(data, item):
    try:
        data['thematic_areas'] = list(
            get_thematic_areas_data(item.thematic_areas))
    except AttributeError:
        pass


def add_dates(data, item):
    # TODO formatar a data para ser serializável
    try:
        data['start_date'] = item.date
        data['end_date'] = item.date
        return
    except AttributeError:
        pass

    try:
        data['start_date'] = item.start_date
        data['end_date'] = item.end_date
        return
    except AttributeError:
        pass


def get_thematic_areas_data(thematic_areas):
    for thematic_area in thematic_areas:
        yield {
            "level0": thematic_area.level0,
            "level1": thematic_area.level1,
            "level2": thematic_area.level2,
        }


def get_institutions_data(institutions):
    for institution in institutions:
        yield {
            "name": institution.name,
            "acronym": institution.acronym,
            "location": {
                "city": institution.location.city,
                "state": institution.location.state,
                "region": institution.location.region,
                "country": institution.location.country,
            },
        }


def get_locations_data(locations):
    for location in locations:
        yield {
            "city": location.city,
            "state": location.state,
            "region": location.region,
            "country": location.country,
        }


def format_query_result_as_rows(items):
    """
    Formata o resultado da consulta como "jsonl"

    Parameters
    ----------
    items : resultado da consulta

    Returns
    -------
    generator de items formatado como "jsonl"
    """
    for item in items:
        data = {}
        add_practice(data, item)
        add_action(data, item)
        add_classification(data, item)
        add_dates(data, item)

        for institution in item.institutions:
            row_institution = get_institution_row(institution)

            for location in item.locations:
                row_location = get_location_row(location)
                for thematic_area in item.thematic_areas:
                    row = {}
                    row.update(data)
                    row.update(row_institution)
                    row.update(row_location)
                    row.update(get_thematic_area_row(thematic_area))

                    yield row


def get_thematic_area_row(thematic_area):
    row = {}
    row["thematic_area_level0"] = thematic_area.level0
    row["thematic_area_level1"] = thematic_area.level1
    row["thematic_area_level2"] = thematic_area.level2
    return row


def get_institution_row(institution):
    row = {}
    row['institution_name'] = institution.name
    row['institution_acronym'] = institution.acronym
    row['institution_city'] = institution.location.city
    row['institution_state'] = institution.location.state
    row['institution_region'] = institution.location.region
    row['institution_country'] = institution.location.country
    return row


def get_location_row(location):
    row = {}
    row["city"] = location.city
    row["state"] = location.state
    row["region"] = location.region
    row["country"] = location.country
    return row
