
import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils.translation import gettext as _

from article import models
from indicator import choices
from indicator.models import Indicator
from indicator.scheduler import delete_tasks, get_or_create_periodic_task
from institution.models import Institution
from location.models import Location
from usefulmodels.models import Action, Practice, ThematicArea


class SciProd:
    def __init__(
        self,
        begin_year=None,
        end_year=None,
        institution__name=None,
        thematic_area__level0=None,
        thematic_area__level1=None,
        location__state__code=None,
        location__state__region=None,
        by_open_access_status=False,
        by_license=False,
        by_institution=False,
        by_thematic_area_level0=False,
        by_thematic_area_level1=False,
        by_state=False,
        by_region=False,
        by_apc=False,
    ):

        self.GROUP_BY_AND_ATTRIBUTE_NAME = dict(
            by_license="license__name",
            by_open_access_status="open_access_status",
            by_institution="institution__name",
            by_thematic_area_level0="thematic_areas__level0",
            by_thematic_area_level1="thematic_areas__level1",
            by_state="state__acronym",
            by_region="state__region",
            by_apc="apc",
        )
        self.ATTRIBUTE_LABEL = dict(
            license__name=_("licença de uso"),
            open_access_status=_("status de acesso aberto"),
            institution__name=_("instituição"),
            thematic_area__level0=_("área temática"),
            thematic_area__level1=_("área temática"),
            state__acronym=_("UF"),
            state__region=_("região"),
            apc=_("APC"),
        )
        self._contribution = set()

        year = datetime.now().year
        self.begin_year = str(begin_year or (year - 10))
        self.end_year = str(end_year or year)

        self.institution__name = institution__name
        self.thematic_area__level0 = thematic_area__level0
        self.thematic_area__level1 = thematic_area__level1
        self.location__state__code = location__state__code
        self.location__state__region = location__state__region
        self.by_license = by_license
        self.by_open_access_status = by_open_access_status
        self.by_institution = by_institution
        self.by_thematic_area_level0 = by_thematic_area_level0
        self.by_thematic_area_level1 = by_thematic_area_level1
        self.by_state = by_state
        self.by_region = by_region
        self.by_apc = by_apc
        self.by_year = bool(begin_year and end_year and begin_year < end_year)

    @property
    def filter_params(self):
        """
        Filtros para selecionar os registros para os quais serão gerados
        os indicadores

        Pode retornar `{}` (dicionário vazio)

        """
        _data = dict(
            begin_year=self.begin_year,
            end_year=self.end_year,
            institution__name=self.institution__name,
            location__state__code=self.location__state__code,
            location__state__region=self.location__state__region,
            thematic_area__level0=self.thematic_area__level0,
            thematic_area__level1=self.thematic_area__level1,
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
            by_open_access_status=self.by_open_access_status,
            by_license=self.by_license,
            by_institution=self.by_institution,
            by_thematic_area_level0=self.by_thematic_area_level0,
            by_thematic_area_level1=self.by_thematic_area_level1,
            by_state=self.by_state,
            by_region=self.by_region,
            by_apc=self.by_apc,
        )
        return {k: v for k, v in _data.items() if v}

    @property
    def series_parameters(self):
        """
        Obtém os dados das séries do gráfico, mas somente para os campos
        elencados pelo `group_by_params`:
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
        Retorna ["year"] para compor o eixo Y do gráfico
        """
        return ["year"]

    @property
    def aditional_group_by_params(self):
        """
        Retorna indicação de mais parâmetros para o "group_by" das séries
        Para artigos não é necessário
        """
        names = dict(
            by_institution=self.by_institution,
            by_thematic_area_level1=self.by_thematic_area_level1,
            by_state=self.by_state,
            by_apc=self.by_apc,
            by_license=self.by_license,
            by_open_access_status=self.by_open_access_status,
        )
        for k, v in names.items():
            if v:
                return {k: True}
        return {"by_open_access_status": True, "by_license": True, "by_apc": True}


    @property
    def category_name(self):
        """
        Retorna o nome da categoria para compor o título do indicador:

        Número de ações por `category_name`

        por exemplo, `instituição`
        """
        names = [
            "by_institution",
            "by_open_access_status",
            "by_thematic_area_level0",
            "by_thematic_area_level1",
            "by_state",
            "by_region",
            "by_license",
            "by_apc",
        ]
        return " / ".join([
            self.ATTRIBUTE_LABEL[self.GROUP_BY_AND_ATTRIBUTE_NAME[k]]
            for k in self.group_by_params.keys() if k in names]
        )

    @property
    def items(self):
        if not hasattr(self, "_items"):
            self._items = models.Article.filter_items_to_generate_indicators(
                **self.filter_params
            )
        return self._items

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
        Retorna os itens resultantes de filtragem e agrupamento aplicado em Article
        """

        for serie_params in self.series_parameters:
            grouped_by = models.Article.parameters_for_values(**serie_params["grouped_by_params"])
            logging.info(f"grouped_by {grouped_by}")
            for item in models.Article.group(self.items, grouped_by):
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
        yield from self.items

    def get_source(self):
        """
        Retorna os nomes das fontes dos dados usados para
        gerar os indicadores
        """
        sources = []
        for item in (
            self.items.values("sources__name")
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        ):
            sources.append(item["sources__name"])
        return " • ".join(sources)


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

    def generate_article_evolution_indicator(self, creator):
        """
        Gera o indicador de evolução do número de artigos
        segundo os filtros e os agrupamentos fornecidos
        """
        indicator_productor = "OCABr"
        measurement = choices.EVOLUTION
        object_name = _("artigos científicos")
        action = Action.objects.get(name="evolução da produção científica")
        practice = Practice.objects.get(name="literatura em acesso aberto")

        raw_data_items = self.get_raw_data()
        summarized = self.get_summarized()
        # if len(summarized) < 2:
        #     logging.warning("Insuficient data")
        #     return

        sources = self.get_source()

        indicator = Indicator.create(
            creator,
            source=indicator_productor,
            object_name=object_name,
            measurement=measurement,
            category=self.category_name,
            context=self.context,
            start_date_year=self.begin_year,
            end_date_year=self.end_year,
            title=None,
            action=action,
            classification="journal-article",
            practice=practice,
            keywords=self.keywords,
            institutions=self.institutions,
            locations=self.locations,
            thematic_areas=self.thematic_areas,
        )
        indicator.summarized = summarized
        indicator.description = _(
            f"Gerado automaticamente usando dados provenientes de {sources}"
        )
        indicator.add_raw_data(raw_data_items)
        return indicator


def generate_indicator(
    creator,
    begin_year=None,
    end_year=None,
    institution__name=None,
    thematic_area__level0=None,
    thematic_area__level1=None,
    location__state__code=None,
    location__state__region=None,
    by_open_access_status=False,
    by_license=False,
    by_institution=False,
    by_thematic_area_level0=False,
    by_thematic_area_level1=False,
    by_state=False,
    by_region=False,
    by_apc=False,
):

    """
    Fornece os parâmetros para obter os dados dos artigos e
    gera o indicador
    """
    sciprod = SciProd(
        begin_year=begin_year,
        end_year=end_year,
        institution__name=institution__name,
        thematic_area__level0=thematic_area__level0,
        thematic_area__level1=thematic_area__level1,
        location__state__code=location__state__code,
        location__state__region=location__state__region,
        by_open_access_status=by_open_access_status,
        by_license=by_license,
        by_institution=by_institution,
        by_thematic_area_level0=by_thematic_area_level0,
        by_thematic_area_level1=by_thematic_area_level1,
        by_state=by_state,
        by_region=by_region,
        by_apc=by_apc,
    )
    return sciprod.generate_article_evolution_indicator(creator)


def get_filter_params(filter_by):
    if filter_by == "thematic_area":
        return get_thematic_area_filter_params()
    if filter_by == "location":
        return get_location_filter_params()
    if filter_by == "institution":
        return get_institution_filter_params()
    return [{}]


def generate_indicators(creator, filter_by, group_by_params, begin_year, end_year):
    """
    Gera os indicadores da combinação dos parâmetros:

    - action__names
    - filter_params
    - group_by_params
    """
    filter_params = get_filter_params(filter_by)
    for params in get_indicator_parameters(filter_params, group_by_params):
        logging.info("Generating indicator for {}".format(params))
        generate_indicator(creator, begin_year, end_year, **params)


def get_indicator_parameters(filter_params, group_by_params):
    """
    Retorna as combinação de 3 itens:
    - action__name
    - parâmetros para filtrar registros
    - parâmetros para agrupar e contar as ocorrências agrupadas
    """
    for f_params in filter_params:
        params = {}
        params.update(f_params)
        params.update(group_by_params)
        yield params


def get_thematic_area_filter_params():
    """
    Retorna um gerador de parâmetros para
    Models.filter_items_to_generate_indicators (Model.objects.filter()),
    sendo Model qualquer `*Directory` (Education, Event, ...)
    """
    try:
        for item in models.Article.objects.filter(
                Q(contributors__affiliations__country__acron2="BR") |
                Q(contributors__affiliations__official__location__country__acron2="BR")
            ).values("contributors__thematic_area__level1").annotate(count=Count("id")):
            logging.info(item)
            yield {"thematic_area__level1": item["contributors__thematic_area__level1"]}
    except:
        yield from []


def get_location_filter_params():
    """
    Retorna um gerador de parâmetros para
    Models.filter_items_to_generate_indicators (Model.objects.filter()),
    sendo Model qualquer `*Directory` (Education, Event, ...)
    """
    try:
        for item in models.Article.objects.filter(
                Q(contributors__affiliations__country__acron2="BR") |
                Q(contributors__affiliations__official__location__country__acron2="BR")
            ).values("contributors__affiliations__official__location__state__acronym").annotate(count=Count("id")):
            logging.info(item)
            yield {"location__state__code": item["contributors__affiliations__official__location__state__acronym"]}
    except Exception as e:
        logging.info(e)
        yield from []


def get_institution_filter_params():
    """
    Retorna um gerador de parâmetros para
    Models.filter_items_to_generate_indicators (Model.objects.filter()),
    sendo Model qualquer `*Directory` (Education, Event, ...)
    """
    try:
        for item in models.Article.objects.filter(
                Q(contributors__affiliations__country__acron2="BR") |
                Q(contributors__affiliations__official__location__country__acron2="BR")
            ).values("contributors__affiliations__official__name").annotate(count=Count("id")):
            logging.info(item)
            yield {"institution__name": item["contributors__affiliations__official__name"]}
    except:
        yield from []


def schedule_indicators_tasks(
    begin_year=None,
    end_year=None,
    user_id=None,
    day_of_week=None,
    hour=None,
    minute=None,
):
    # TODO obter o usuário corrente
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except:
        user = User.objects.first()

    task = _("Geração de indicadores de artigos científicos")

    year = datetime.now().year
    begin_year = begin_year or str(year - 11)
    end_year = end_year or str(year)

    delete_tasks(task)

    # TODO thematic_area ainda não está no modelo
    filters = {
        None: {
            # "by_thematic_area_level1": True,
            "by_state": True,
            "by_institution": True
        },
        "location": {
            # "by_thematic_area_level1": True,
            "by_institution": True
        },
        "institution": {
            # "by_thematic_area_level1": True,
            "by_state": True,
        },
        # "thematic_area": {
        #     "by_institution": True, "by_state": True
        # },
    }

    for filter_by, group_by in filters.items():

        # mais parâmetros menos prioridade por ser mais rápido
        priority = 1 + len(group_by)

        params = {}
        params["creator_id"] = user.id
        params["begin_year"] = begin_year
        params["end_year"] = end_year
        params["filter_by"] = filter_by
        params["group_by"] = group_by
        logging.info("Scheduling task {} {}".format(task, params))
        get_or_create_periodic_task(
            name=get_task_title(task, filter_by, group_by, begin_year, end_year),
            task=task,
            kwargs=params,
            day_of_week=day_of_week or 5,
            hour=hour or 21,
            minute=minute or 0,
            priority=priority,
            enabled=True,
            only_once=False,
        )


def get_task_title(task, filter_by, group_by, begin_year, end_year):
    filter_by = filter_by or "sem filtro"
    group_by = "/".join(group_by.keys())

    return f"{task} ({filter_by}, {group_by}, {begin_year}-{end_year})"
