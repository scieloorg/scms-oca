from itertools import product
import logging

from django.core.files.base import ContentFile
from django.db.models import Count
from django.utils.translation import gettext as _
from django.db.models.functions import Upper
from django.contrib.auth import get_user_model

from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory
from usefulmodels.models import Action, ThematicArea, State
from indicator.models import Indicator
from indicator import choices
from institution.models import Institution
from location.models import Location
from indicator.scheduler import get_or_create_periodic_task


class DataDirectory:
    def __init__(
        self,
        action__name=None,
        institution__name=None,
        thematic_area__level0=None,
        thematic_area__level1=None,
        location__state__code=None,
        location__state__region=None,
        by_practice=False,
        by_classification=False,
        by_institution=False,
        by_thematic_area_level0=False,
        by_thematic_area_level1=False,
        by_state=False,
        by_region=False,
    ):

        by_practice = True
        by_classification = True

        self.GROUP_BY_AND_ATTRIBUTE_NAME = dict(
            by_classification="classification",
            by_institution="institution__name",
            by_practice="practice__name",
            by_thematic_area_level0="thematic_areas__level0",
            by_thematic_area_level1="thematic_areas__level1",
            by_state="state__acronym",
            by_region="state__region",
        )
        self.ATTRIBUTE_LABEL = dict(
            practice__name=_("prática"),
            classification=_("qualificação"),
            institution__name=_("instituição"),
            thematic_area_level0=_("área temática"),
            thematic_areas__level1=_("área temática"),
            state__acronym=_("UF"),
            state__region=_("região"),
        )
        self._contribution = set()
        self.action__name = action__name
        self.institution__name = institution__name
        self.thematic_area__level0 = thematic_area__level0
        self.thematic_area__level1 = thematic_area__level1
        self.location__state__code = location__state__code
        self.location__state__region = location__state__region
        self.by_practice = by_practice
        self.by_classification = by_classification
        self.by_institution = by_institution
        self.by_thematic_area_level0 = by_thematic_area_level0
        self.by_thematic_area_level1 = by_thematic_area_level1
        self.by_state = by_state
        self.by_region = by_region

    @property
    def filter_params(self):
        """
        Filtros para selecionar os registros para os quais serão gerados
        os indicadores

        Pode retornar `{}` (dicionário vazio)

        """
        _data = dict(
            action__name=self.action__name,
            institution__name=self.institution__name,
            thematic_area__level0=self.thematic_area__level0,
            thematic_area__level1=self.thematic_area__level1,
            location__state__code=self.location__state__code,
            location__state__region=self.location__state__region,
        )
        return {k: v for k, v in _data.items() if v}

    @property
    def context(self):
        """
        Obtém o contexto a partir dos valores de alguns filtros (`self.filter_params`).

        Pode retornar `''` (str vazia)
        """
        _data = dict(
            institution__name=self.institution__name,
            thematic_area__level0=self.thematic_area__level0,
            thematic_area__level1=self.thematic_area__level1,
            location__state__code=self.location__state__code,
            location__state__region=self.location__state__region,
        )
        return " | ".join([value for value in _data.values() if value])

    @property
    def group_by_params(self):
        """
        Parâmetros para indicar os campos a serem usados na execução
        do "group_by" nos registros selecionados pelos filtros e
        para os quais serão gerados os indicadores

        Pode retornar `{}` (dicionário vazio)

        """
        _data = dict(
            by_classification=self.by_classification,
            by_practice=self.by_practice,
            by_institution=self.by_institution,
            by_thematic_area_level0=self.by_thematic_area_level0,
            by_thematic_area_level1=self.by_thematic_area_level1,
            by_state=self.by_state,
            by_region=self.by_region,
        )
        return {k: v for k, v in _data.items() if v}

    @property
    def series_parameters(self):
        """
        Obtém os dados das séries do gráfico para compor o eixo X,
        mas somente para os campos selecionados pelo `group_by_params`:
        - qualificação da ação
        - prática
        - instituição (nome)
        - área temática (níveis 0 e 1)
        - localidade (estado)

        Retorna um gerador de séries
        """
        for k, v in self.group_by_params.items():
            name = self.GROUP_BY_AND_ATTRIBUTE_NAME.get(k)
            if name not in self.y_params:
                params = {k: True}
                params.update(self.aditional_group_by_params or {})
                yield {
                    "name": name,
                    "grouped_by_params": params,
                }

    @property
    def y_params(self):
        """
        Retorna o nome de um dos campos indicados por "group_by_params"
        para compor o eixo Y do gráfico
        São os campos que podem ter maior ocorrência como:
        - instituição
        - UF
        Na ausência destes, retorna `classification`
        """
        names = dict(
            by_institution="institution__name",
            # by_thematic_area_level0="thematic_areas__level0",
            # by_thematic_area_level1="thematic_areas__level1",
            by_state="state__acronym",
            # by_region="locations__state__region",
        )
        for k, v in names.items():
            if self.group_by_params.get(k):
                return [v]
        return ["classification"]

    @property
    def aditional_group_by_params(self):
        """
        Retorna indicação de mais parâmetros para o "group_by" das séries
        """
        names = dict(
            by_institution=self.by_institution,
            by_thematic_area_level1=self.by_thematic_area_level1,
            by_state=self.by_state,
        )
        for k, v in names.items():
            if v:
                return {k: True}
        return {"by_classification": True}

    @property
    def category_name(self):
        """
        Retorna o nome da categoria para compor o título do indicador:

        Número de ações por `category_name`

        por exemplo, `instituição`
        """
        names = [
            "by_institution",
            "by_thematic_area_level0",
            "by_thematic_area_level1",
            "by_state",
            "by_region",
        ]
        return " / ".join([
            self.ATTRIBUTE_LABEL[self.GROUP_BY_AND_ATTRIBUTE_NAME[k]]
            for k in self.group_by_params.keys() if k in names]
        )

    @property
    def education_items(self):
        """
        Resultado da consulta em `EducationDirectory` filtrado por `self.filter_params`
        """
        if not hasattr(self, "_education_items"):
            self._education_items = (
                EducationDirectory.filter_items_to_generate_indicators(
                    **self.filter_params
                )
            )
        return self._education_items

    @property
    def dissemination_items(self):
        """
        Resultado da consulta em `EventDirectory` filtrado por `self.filter_params`
        """
        if not hasattr(self, "_dissemination_items"):
            self._dissemination_items = (
                EventDirectory.filter_items_to_generate_indicators(**self.filter_params)
            )
        return self._dissemination_items

    @property
    def infrastructure_items(self):
        """
        Resultado da consulta em `InfrastructureDirectory` filtrado por `self.filter_params`
        """
        if not hasattr(self, "_infrastructure_items"):
            self._infrastructure_items = (
                InfrastructureDirectory.filter_items_to_generate_indicators(
                    **self.filter_params
                )
            )
        return self._infrastructure_items

    @property
    def policy_items(self):
        """
        Resultado da consulta em `PolicyDirectory` filtrado por `self.filter_params`
        """
        if not hasattr(self, "_policy_items"):
            self._policy_items = PolicyDirectory.filter_items_to_generate_indicators(
                **self.filter_params
            )
        return self._policy_items

    @classmethod
    def _standardize_institution_attribute_name(cls, item):
        """
        Padroniza os nomes dos campos dos *Directory nos resultados da execução do group_by
        """
        keys_to_replace = [k for k in item.keys() if k.startswith("organization") or k.startswith("institutions")]
        for k in keys_to_replace:
            key = k.replace("organization", "institutions")
            key = key.replace("institutions__name", "institution__name")
            item[key] = item.pop(k)
        return item

    def _standardize_location_attribute_name(self, item):
        """
        Padroniza os nomes dos campos dos *Directory nos resultados da execução do group_by
        """
        keys_to_replace = [k for k in item.keys() if "location" in k]
        for k in keys_to_replace:
            key = k.replace("locations__", "")
            key = key.replace("institutions__location__", "")
            key = key.replace("institution__location__", "")
            item[key] = item.pop(k)
        return item

    def get_summarized(self):
        """
        Constrói dicionário com dados para o gráfico
        """
        summarized = {}
        summarized["items"] = list(self.get_series())
        try:
            summarized["table_header"] = list(summarized["items"][0].keys())
        except IndexError:
            return {}
        summarized["graphic_data"] = list(self.graphic_data)
        summarized["version"] = "v2.0"
        # summarized["graphic"] = self.get_data_for_graphic
        return summarized

    def get_series(self):
        """
        Retorna os dados das series
        """
        for serie_params in self.series_parameters:
            yield from self.summarize(serie_params, EducationDirectory, self.education_items)
            yield from self.summarize(serie_params, EventDirectory, self.dissemination_items)
            yield from self.summarize(serie_params, InfrastructureDirectory, self.infrastructure_items)
            yield from self.summarize(serie_params, PolicyDirectory, self.policy_items)

    def summarize(
        self,
        serie_params,
        model,
        query_result,
    ):
        """
        Retorna os itens resultantes de filtragem e agrupamento aplicado em `model`
        """
        grouped_by = model.parameters_for_values(**serie_params["grouped_by_params"])
        summarized = model.group(query_result, grouped_by)
        for item in summarized:
            if not item:
                continue
            self._standardize_institution_attribute_name(item)
            self._standardize_location_attribute_name(item)
            item["stack"] = serie_params["name"]
            yield item

    def get_y_label(self, item):
        """
        Obtém o rótulo para os componentes do eixo Y
        """
        return " | ".join([item[k] for k in self.y_params if item.get(k)])

    def get_x_label(self, item):
        """
        Obtém o rótulo para os componentes do eixo X
        """
        label = self.ATTRIBUTE_LABEL.get(item["stack"])
        return item[item["stack"]] or f'NA ({label})'

    @property
    def graphic_data(self):
        """
        Retorna os itens preparados para serem usados para montar o gráfico
        """
        for item in self.get_series():

            logging.info("Data graphic {}".format(item))
            x_label = self.get_x_label(item)
            y_label = self.get_y_label(item)

            yield {
                "x": x_label,
                "y": y_label,
                "count": item["count"],
                "stack": item["stack"],
            }

    def get_raw_data(self):
        """
        Retorna os registros resultantes da filtragem (dados brutos)
        """
        for item in self.education_items.iterator():
            self._contribution.add(item.institutional_contribution)
            yield item

        for item in self.dissemination_items.iterator():
            self._contribution.add(item.institutional_contribution)
            yield item

        for item in self.infrastructure_items.iterator():
            self._contribution.add(item.institutional_contribution)
            yield item

        for item in self.policy_items.iterator():
            self._contribution.add(item.institutional_contribution)
            yield item

    def get_contribution(self):
        """
        Retorna os nomes das instituições fornecedora dos dados usados para
        gerar os indicadores
        """
        return " • ".join(sorted(self._contribution)) or "SciELO"

    @property
    def institutions(self):
        """
        Retorna os registros das instituições se a consulta filtrou por nome da instituição
        """
        try:
            return Institution.objects.filter(
                name=self.filter_params["institution__name"]
            ).iterator()
        except KeyError:
            pass

    @property
    def thematic_areas(self):
        """
        Retorna os registros das áreas temáticas se a consulta filtrou por áreas temáticas
        """
        try:
            return ThematicArea.objects.filter(
                level1=self.filter_params["thematic_area__level1"]
            ).iterator()
        except KeyError:
            try:
                return ThematicArea.objects.filter(
                    level0=self.filter_params["thematic_area__level0"]
                ).iterator()
            except KeyError:
                pass

    @property
    def locations(self):
        """
        Retorna os registros das localidades se a consulta filtrou por estado ou região
        """
        try:
            return Location.objects.filter(
                state__acronym=self.filter_params["location__state__code"]
            ).iterator()
        except KeyError:
            try:
                return Location.objects.filter(
                    state__region=self.filter_params["location__state__region"]
                ).iterator()
            except KeyError:
                pass

    @property
    def keywords(self):
        """
        Usa como keywords os valores dos filtros usados na consulta
        """
        return list(self.filter_params.values()) or [_("Brasil")]

    @property
    def action_label(self):
        if self.action__name.startswith("políticas"):
            return self.action__name
        return _("ações de {}").format(self.action__name)

    def generate_frequency_indicator(self, creator, min_items=None):
        """
        Gera o indicador do número de ações
        (educação, disseminação, infraestrutura, políticas)
        segundo os filtros e os agrupamentos fornecidos
        """
        indicator_productor = "OCABr"
        measurement = choices.FREQUENCY
        object_name = self.action_label
        action = self.action__name and Action.objects.get(name=self.action__name)

        summarized = self.get_summarized()
        min_items = min_items or 10
        if len(summarized.get("items") or []) < min_items:
            logging.warning("Insuficient data")
            return

        contribution = self.get_contribution()

        indicator = Indicator.create(
            creator,
            source=indicator_productor,
            object_name=object_name,
            measurement=measurement,
            category=self.category_name,
            context=self.context,
            start_date_year=None,
            end_date_year=None,
            title=None,
            action=action,
            classification=None,
            practice=None,
            keywords=self.keywords,
            institutions=self.institutions,
            locations=self.locations,
            thematic_areas=self.thematic_areas,
        )
        indicator.summarized = summarized
        indicator.description = _(
            f"Gerado automaticamente usando dados coletados e registrados manualmente por {contribution}"
        )

        raw_data_items = self.get_raw_data()
        indicator.add_raw_data(raw_data_items)
        return indicator


def generate_indicator(
    creator,
    action__name=None,
    institution__name=None,
    thematic_area__level0=None,
    thematic_area__level1=None,
    location__state__code=None,
    location__state__region=None,
    by_practice=False,
    by_classification=False,
    by_institution=False,
    by_thematic_area_level0=False,
    by_thematic_area_level1=False,
    by_state=False,
    by_region=False,
    min_items=None,
):
    """
    Fornece os parâmetros para obter os dados das ações (diretórios) e
    gera o indicador
    """
    directory = DataDirectory(
        action__name=action__name,
        institution__name=institution__name,
        thematic_area__level0=thematic_area__level0,
        thematic_area__level1=thematic_area__level1,
        location__state__code=location__state__code,
        location__state__region=location__state__region,
        by_practice=by_practice,
        by_classification=by_classification,
        by_institution=by_institution,
        by_thematic_area_level0=by_thematic_area_level0,
        by_thematic_area_level1=by_thematic_area_level1,
        by_state=by_state,
        by_region=by_region,
    )
    return directory.generate_frequency_indicator(creator, min_items)


def generate_indicators(creator, action__names, filter_by, group_by_params, min_items=None):
    """
    Gera os indicadores da combinação dos parâmetros:

    - action__names
    - filter_params
    - group_by_params
    """
    filter_params = [{}]
    if filter_by == "thematic_area":
        filter_params = get_thematic_area_filter_params()
    elif filter_by == "location":
        filter_params = get_location_filter_params()

    for params in get_indicator_parameters(
        action__names, filter_params, group_by_params
    ):
        logging.info("Generating indicator for {}".format(params))
        params["min_items"] = min_items
        generate_indicator(creator, **params)


def get_indicator_parameters(action__names, filter_params, group_by_params):
    """
    Retorna as combinação de 3 itens:
    - action__name
    - parâmetros para filtrar registros
    - parâmetros para agrupar e contar as ocorrências agrupadas
    """
    for action__name, f_params in product(action__names, filter_params):
        params = {}
        params["action__name"] = action__name
        params.update(f_params)
        params.update(group_by_params)
        yield params


def get_thematic_area_filter_params():
    """
    Retorna as áreas temáticas para serem usadas como valor para `objects.filter`
    """
    yield from (
        {"thematic_area__level1": item["level1"]} for item in ThematicArea.values()
    )


def get_location_filter_params():
    """
    Retorna os códigos das Unidades Federativas para serem usados como valor para `objects.filter`
    """
    yield from (
        {"location__state__code": item["acronym"]} for item in State.values(["acronym"])
    )


def schedule_indicators_tasks(
    min_items=None,
    user_id=None,
    day_of_week=None,
    hour=None,
    minute=None,
):
    """
    Cria tarefas de geração de indicadores e as agenda.
    Cada tarefa gerará uma série de indicadores de acordo com o nome da tarefa.
    O nome da tarefa contém:
    - nome da ação ou 'todas'
    - 'sem filtro' ou thematic_area ou location
    - by_thematic_area_level1 / by_state / by_institution

    Exemplo:
    A tarefa cujo nome é
    "Geração de indicadores de ações
    (políticas públicas e institucionais, thematic_area, by_state / by_institution)
    "
    gerará, para cada área temática, um registro de indicador de políticas,
    agrupadas por UF e instituições
    """
    # TODO obter o usuário corrente
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except:
        user = User.objects.first()

    task = _("Geração de indicadores de ações")

    actions = [
        None,
        "políticas públicas e institucionais",
        "infraestrutura",
        "educação / capacitação",
        "disseminação",
    ]

    filter_groups = {
        None: [
            {"by_thematic_area_level1": True, "by_state": True, "by_institution": True},
        ],
        "thematic_area": [
            {"by_state": True, "by_institution": True},
        ],
        "location": [
            {"by_thematic_area_level1": True, "by_institution": True},
        ],
    }
    for filter_by, groups in filter_groups.items():

        for action, group_by in product(actions, groups):
            # mais parâmetros menos prioridade por ser mais rápido
            priority = 1 + len(group_by)

            params = {}
            params["creator_id"] = user.id
            params["action_name"] = action
            params["filter_by"] = filter_by
            params["group_by"] = group_by
            params["min_items"] = min_items

            task_name = get_task_title(task, action, filter_by, group_by)
            logging.info("Scheduling task {} {} {}".format(task_name, task, params))
            get_or_create_periodic_task(
                name=task_name,
                task=task,
                kwargs=params,
                day_of_week=day_of_week or 5,
                hour=hour or 21,
                minute=minute or 0,
                priority=priority,
                enabled=True,
                only_once=False,
            )


def get_task_title(task, action, filter_by, group_by):
    action = action or "todas"
    filter_by = filter_by or "sem filtro"
    group_by = "/".join(group_by.keys())

    return f"{task} ({action}, {filter_by}, {group_by})"
