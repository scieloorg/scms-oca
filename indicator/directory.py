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
        location__region=None,
        by_practice=False,
        by_classification=False,
        by_institution=False,
        by_thematic_area_level0=False,
        by_thematic_area_level1=False,
        by_state=False,
        by_region=False,
    ):
        by_classification = True
        logging.info(
            dict(
                action__name=action__name,
                institution__name=institution__name,
                thematic_area__level0=thematic_area__level0,
                thematic_area__level1=thematic_area__level1,
                location__state__code=location__state__code,
                location__region=location__region,
                by_practice=by_practice,
                by_classification=by_classification,
                by_institution=by_institution,
                by_thematic_area_level0=by_thematic_area_level0,
                by_thematic_area_level1=by_thematic_area_level1,
                by_state=by_state,
                by_region=by_region,
            )
        )
        # by_practice = not (
        #     by_institution
        #     and by_thematic_area_level0
        #     and thematic_area__level1
        #     and by_state
        #     and by_region
        # )
        self._contribution = set()
        self.action__name = action__name
        self.institution__name = institution__name
        self.thematic_area__level0 = thematic_area__level0
        self.thematic_area__level1 = thematic_area__level1
        self.location__state__code = location__state__code
        self.location__region = location__region
        self.by_practice = by_practice
        self.by_classification = by_classification
        self.by_institution = by_institution
        self.by_thematic_area_level0 = by_thematic_area_level0
        self.by_thematic_area_level1 = by_thematic_area_level1
        self.by_state = by_state
        self.by_region = by_region

    @property
    def filter_params(self):
        # obtém os parametros para filtrar os registros
        _data = dict(
            action__name=self.action__name,
            institution__name=self.institution__name,
            thematic_area__level0=self.thematic_area__level0,
            thematic_area__level1=self.thematic_area__level1,
            location__state__code=self.location__state__code,
            location__region=self.location__region,
        )
        return {k: v for k, v in _data.items() if v}

    @property
    def scope_data(self):
        # obtém os parametros para obter o contexto
        _data = dict(
            institution__name=self.institution__name,
            thematic_area__level0=self.thematic_area__level0,
            thematic_area__level1=self.thematic_area__level1,
            location__state__code=self.location__state__code,
            location__region=self.location__region,
        )
        return {k: v for k, v in _data.items() if v}

    @property
    def scope_value(self):
        return " | ".join(self.scope_data.values())

    @property
    def group_by_params(self):
        # obtém os parametros para agrupar os registros
        _data = dict(
            by_practice=self.by_practice,
            by_classification=self.by_classification,
            by_institution=self.by_institution,
            by_thematic_area_level0=self.by_thematic_area_level0,
            by_thematic_area_level1=self.by_thematic_area_level1,
            by_state=self.by_state,
            by_region=self.by_region,
        )
        return {k: v for k, v in _data.items() if v}

    @property
    def y_params(self):
        _data = dict(
            by_practice="practice__name",
            by_institution="institutions__name",
            by_thematic_area_level0="thematic_areas__level0",
            by_thematic_area_level1="thematic_areas__level1",
            by_state="locations__state__acronym",
            by_region="locations__state__region",
        )
        params = [v for k, v in _data.items() if self.group_by_params.get(k)]
        if not params:
            params = ["classification"]
        return params

    @property
    def x_params(self):
        if self.y_params == ["classification"]:
            return ["action__name"]
        return ["classification"]

    @property
    def category_name(self):
        names = dict(
            by_practice=_("prática"),
            # by_classification=_("qualificação"),
            by_institution=_("instituição"),
            by_thematic_area_level0=_("área temática 0"),
            by_thematic_area_level1=_("área temática 1"),
            by_state=_("UF"),
            by_region=_("região"),
        )
        return ", ".join(
            [names[k] for k, v in self.group_by_params.items() if v and names.get(k)]
        )

    @property
    def education_items(self):
        if not hasattr(self, "_education_items"):
            self._education_items = (
                EducationDirectory.filter_items_to_generate_indicators(
                    **self.filter_params
                )
            )
        return self._education_items

    @property
    def dissemination_items(self):
        if not hasattr(self, "_dissemination_items"):
            self._dissemination_items = (
                EventDirectory.filter_items_to_generate_indicators(**self.filter_params)
            )
        return self._dissemination_items

    @property
    def infrastructure_items(self):
        if not hasattr(self, "_infrastructure_items"):
            self._infrastructure_items = (
                InfrastructureDirectory.filter_items_to_generate_indicators(
                    **self.filter_params
                )
            )
        return self._infrastructure_items

    @property
    def policy_items(self):
        if not hasattr(self, "_policy_items"):
            self._policy_items = PolicyDirectory.filter_items_to_generate_indicators(
                **self.filter_params
            )
        return self._policy_items

    @classmethod
    def _standardize_institution_attribute_name(cls, item):
        """ """
        keys_to_replace = [k for k in item.keys() if k.startswith("organization")]
        for k in keys_to_replace:
            key = k.replace("organization", "institutions")
            item[key] = item[k]
        return item

    def _standardize_location_attribute_name(self, item):
        keys_to_replace = [k for k in item.keys() if "location" in k]
        for k in keys_to_replace:
            key = k.replace("institutions__location", "locations")
            item[key] = item.get(key) or item[k]
        return item

    def get_summarized(self):
        summarized = {}
        summarized["items"] = list(self.get_summarized_items())
        summarized["graphic_data"] = list(self.graphic_data)
        summarized["table_header"] = list(summarized["items"][0].keys())
        summarized["version"] = "v2.0"
        # summarized["graphic"] = self.get_data_for_graphic
        return summarized

    def get_summarized_items(self):
        yield from self.summarize(EducationDirectory, self.education_items)
        yield from self.summarize(EventDirectory, self.dissemination_items, True)
        yield from self.summarize(InfrastructureDirectory, self.infrastructure_items)
        yield from self.summarize(PolicyDirectory, self.policy_items)

    def summarize(
        self,
        model,
        query_result,
        do_standardize_institution_attribute_name=False,
    ):
        # lower_name=Lower("name")
        grouped_by = model.parameters_for_values(**self.group_by_params)
        summarized = model.group(query_result, grouped_by)

        for item in summarized:
            if not item:
                continue
            if do_standardize_institution_attribute_name:
                self._standardize_institution_attribute_name(item)
            self._standardize_location_attribute_name(item)
            yield item

    def get_x_label(self, item):
        return " | ".join([item[k] for k in self.x_params if item.get(k)])

    def get_y_label(self, item):
        return " | ".join([item[k] for k in self.y_params if item.get(k)])

    @property
    def graphic_data(self):
        y_items = []
        x_items = []

        for item in self.get_summarized_items():

            logging.info("Data graphic {}".format(item))
            x_label = self.get_x_label(item)
            y_label = self.get_y_label(item)

            yield {"x": x_label, "y": y_label, "count": item["count"]}

    def get_raw_data(self):
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
        return " • ".join(sorted(self._contribution)) or "SciELO"

    def get_related(self):
        result = {
            "institutions": None,
            "locations": None,
            "thematic_areas": None,
        }
        try:
            result["institutions"] = Institution.objects.filter(
                name=self.filter_params["institution__name"]
            ).iterator()
        except KeyError:
            pass

        try:
            result["thematic_areas"] = ThematicArea.objects.filter(
                level1=self.filter_params["thematic_area__level1"]
            ).iterator()
        except KeyError:
            try:
                result["thematic_areas"] = ThematicArea.objects.filter(
                    level0=self.filter_params["thematic_area__level0"]
                ).iterator()
            except KeyError:
                pass

        try:
            result["locations"] = Location.objects.filter(
                state__acronym=self.filter_params["location__state__code"]
            ).iterator()
        except KeyError:
            try:
                result["locations"] = Location.objects.filter(
                    state__region=self.filter_params["location__region"]
                ).iterator()
            except KeyError:
                pass
        return result

    def get_keywords(self):
        return list([item for item in self.filter_params.values() if item]) or [
            _("Brasil")
        ]

    def generate_frequency_indicator(self, creator):
        indicator_productor = "OCABr"
        measurement = choices.FREQUENCY
        object_name = None if self.action__name else "ações"
        action = self.action__name and Action.objects.get(name=self.action__name)

        raw_data_items = self.get_raw_data()
        summarized = self.get_summarized()
        if len(summarized) < 2:
            logging.warning("Insuficient data")
            return

        keywords = self.get_keywords()
        related = self.get_related()
        contribution = self.get_contribution()

        indicator = Indicator.create(
            creator,
            source=indicator_productor,
            object_name=object_name,
            measurement=measurement,
            category=self.category_name,
            context=self.scope_value,
            start_date_year=None,
            end_date_year=None,
            title=None,
            action=action,
            classification=None,
            practice=None,
            keywords=keywords,
            institutions=related.get("institutions"),
            locations=related.get("locations"),
            thematic_areas=related.get("thematic_areas"),
        )
        indicator.summarized = summarized
        indicator.description = _(
            f"Gerado automaticamente usando dados coletados e registrados manualmente por {contribution}"
        )
        indicator.add_raw_data(raw_data_items)
        return indicator


def generate_indicator(
    creator,
    action__name=None,
    institution__name=None,
    thematic_area__level0=None,
    thematic_area__level1=None,
    location__state__code=None,
    location__region=None,
    by_practice=False,
    by_classification=False,
    by_institution=False,
    by_thematic_area_level0=False,
    by_thematic_area_level1=False,
    by_state=False,
    by_region=False,
):

    directory = DataDirectory(
        action__name=action__name,
        institution__name=institution__name,
        thematic_area__level0=thematic_area__level0,
        thematic_area__level1=thematic_area__level1,
        location__state__code=location__state__code,
        location__region=location__region,
        by_practice=by_practice,
        by_classification=by_classification,
        by_institution=by_institution,
        by_thematic_area_level0=by_thematic_area_level0,
        by_thematic_area_level1=by_thematic_area_level1,
        by_state=by_state,
        by_region=by_region,
    )
    return directory.generate_frequency_indicator(creator)


def generate_indicators(creator, action__names, filter_params, group_by_params):
    for params in get_indicator_parameters(
        action__names, filter_params, group_by_params
    ):
        logging.info("Generating indicator for {}".format(params))
        generate_indicator(creator, **params)


def get_indicator_parameters(action__names, filter_params, group_by_params):
    """
    Retorna as combinação de 3 itens:
    - action__name
    - parâmetros para filtrar registros
    - parâmetros para agrupar e contar as ocorrências agrupadas
    """
    for action__name, f_params in product(action__names, filter_params):
        # pula as combinações de filtrar e agrupar pelo mesmo atributo
        if len(f_params) == len(group_by_params) == 1:
            if f_params.get("institution__name") and group_by_params.get(
                "by_institution"
            ):
                continue
            if f_params.get("location__state__code") and group_by_params.get(
                "by_state"
            ):
                continue
            if f_params.get("thematic_area__level1") and group_by_params.get(
                "by_thematic_area_level1"
            ):
                continue

        params = {}
        params["action__name"] = action__name
        params.update(f_params)
        params.update(group_by_params)
        yield params


def get_thematic_area_filter_params():
    """
    Retorna um gerador de parâmetros para
    Models.filter_items_to_generate_indicators (Model.objects.filter()),
    sendo Model qualquer `*Directory` (Education, Event, ...)
    """
    yield from (
        {"thematic_area__level1": item["level1"]} for item in ThematicArea.values()
    )


def get_location_filter_params():
    """
    Retorna um gerador de parâmetros para
    Models.filter_items_to_generate_indicators (Model.objects.filter()),
    sendo Model qualquer `*Directory` (Education, Event, ...)
    """
    yield from (
        {"location__state__code": item["acronym"]} for item in State.values(["acronym"])
    )


def schedule_indicators_tasks(
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

    task = _("Geração de indicadores de ações em Ciência Aberta")

    actions = [
        None,
        "políticas públicas e institucionais",
        "infraestrutura",
        "educação / capacitação",
        "disseminação",
    ]
    filters = [None, "thematic_area", "location"]

    groups = [
        {},
        {"by_practice": True},
        {"by_thematic_area_level1": True},
        {"by_state": True},
        {"by_institution": True},
        {"by_thematic_area_level1": True, "by_state": True},
        {"by_thematic_area_level1": True, "by_institution": True},
        {"by_state": True, "by_institution": True},
        {"by_thematic_area_level1": True, "by_state": True, "by_institution": True},
    ]

    for action, filter_by, group_by in product(actions, filters, groups):
        # mais parâmetros menos prioridade por ser mais rápido
        priority = 1 + len(group_by)

        params = {}
        params["creator_id"] = user.id
        params["action_name"] = action
        params["filter_by"] = filter_by
        params["group_by"] = group_by
        logging.info("Scheduling task {} {}".format(task, params))
        get_or_create_periodic_task(
            name=get_task_title(task, action, filter_by, group_by),
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
    names = [
        task,
        action or "todas",
        filter_by or "sem filtro",
        "/".join(group_by.keys()),
    ]
    return " ".join([x for x in names if x])
