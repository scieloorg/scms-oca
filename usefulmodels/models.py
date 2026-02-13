from django.db import models
from django.db.models import Count
from django.utils.translation import gettext as _
from django.utils.text import slugify
from core.models import CommonControlField
from usefulmodels.forms import (
    CityForm,
    CountryForm,
    StateForm,
    ThematicAreaForm,
    PracticeForm,
    ActionForm,
)

from . import choices


class City(CommonControlField):
    """
    Represent a list of cities

    Fields:
        name
    """

    name = models.CharField(
        _("Name of the city"), blank=True, null=True, max_length=255
    )

    autocomplete_search_field = "name"

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __unicode__(self):
        return "%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def autocomplete_label(self):
        return str(self)

    @property
    def data(self):
        return {"city__name": self.name}

    @classmethod
    def get_or_create(cls, user, name):
        if cls.objects.filter(name__exact=name).exists():
            try:
                return cls.objects.get(name__exact=name)
            except:
                return cls.objects.filter(name__exact=name).first()
        else:
            city = City()
            city.name = name
            city.creator = user
            city.save()

        return city

    @classmethod
    def values(cls, selected_attributes=None):
        selected_attributes = selected_attributes or [
            "name",
        ]
        return (
            cls.objects.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        )

    base_form_class = CityForm


class State(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        acronym
    """

    name = models.CharField(
        _("Name of the state"), blank=True, null=True, max_length=255
    )
    acronym = models.CharField(
        _("Acronym to the state"), blank=True, null=True, max_length=255
    )
    region = models.CharField(
        _("Region"), choices=choices.regions, max_length=255, null=True, blank=True
    )

    autocomplete_search_field = "name"

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")

    def __unicode__(self):
        return "%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def autocomplete_label(self):
        return str(self)

    @property
    def data(self):
        return {
            "state__name": self.name,
            "state__acronym": self.acronym,
            "state__region": self.region,
        }

    @classmethod
    def get_or_create(cls, user, name=None, acronym=None):
        if name:
            if cls.objects.filter(name__exact=name).exists():
                return cls.objects.get(name__exact=name)

        if acronym:
            if cls.objects.filter(acronym__exact=acronym).exists():
                return cls.objects.get(acronym__exact=acronym)

        state = State()
        state.name = name
        state.acronym = acronym
        state.creator = user
        state.save()

        return state

    @classmethod
    def parameters_for_values(cls, prefix, name, acronym, region):
        params = []
        if name or acronym:
            params += [f"{prefix}__name", f"{prefix}__acronym"]
        if region:
            params += [f"{prefix}__region"]
        return params

    @classmethod
    def values(cls, selected_attributes=None):
        selected_attributes = selected_attributes or ["name", "acronym", "region"]
        return (
            cls.objects.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        )

    base_form_class = StateForm


class Country(CommonControlField):
    """
    Represent the list of Countries

    Fields:
        name
        acronym
    """

    name_pt = models.CharField(
        _("Name of the Country (pt)"), blank=True, null=True, max_length=255
    )
    name_en = models.CharField(
        _("Name of the Country (en)"), blank=True, null=True, max_length=255
    )
    capital = models.CharField(
        _("Capital of the Country"), blank=True, null=True, max_length=255
    )
    acron3 = models.CharField(
        _("Acronym to the Country (3 char)"), blank=True, null=True, max_length=255
    )
    acron2 = models.CharField(
        _("Acronym to the Country (2 char)"), blank=True, null=True, max_length=255
    )

    autocomplete_search_field = "name_pt"

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    def __unicode__(self):
        return "%s" % self.name_pt

    def __str__(self):
        return "%s" % self.name_pt

    def autocomplete_label(self):
        return str(self)

    @property
    def data(self):
        return {
            "country__name_pt": self.name_pt,
            "country__name_en": self.name_en,
            "country__capital": self.capital,
            "country__acron3": self.acron3,
            "country__acron2": self.acron2,
        }

    @classmethod
    def get_or_create(
        cls, user, name_pt=None, name_en=None, capital=None, acron3=None, acron2=None
    ):
        if name_pt:
            if cls.objects.filter(name_pt__exact=name_pt).exists():
                return cls.objects.get(name_pt__exact=name_pt)

        if name_en:
            if cls.objects.filter(name_en__exact=name_en).exists():
                return cls.objects.get(name_en__exact=name_en)

        country = Country()
        country.name_pt = name_pt
        country.name_en = name_en
        country.capital = capital
        country.acron3 = acron3
        country.acron2 = acron2
        country.creator = user
        country.save()

        return country

    @classmethod
    def parameters_for_values(cls, prefix):
        return [
            f"{prefix}__name_pt",
            f"{prefix}__name_en",
            f"{prefix}__capital",
            f"{prefix}__acron3",
            f"{prefix}__acron2",
        ]

    @classmethod
    def values(cls, selected_attributes=None):
        selected_attributes = selected_attributes or [
            "acron2",
        ]
        return (
            cls.objects.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        )

    base_form_class = CountryForm


class ThematicArea(CommonControlField):
    """
    Represent the thematic areas wit 3 levels.

    Fields:
        level 0
        level 1
        level 2
    """

    level0 = models.CharField(
        _("Level 0"),
        choices=choices.thematic_level0,
        max_length=255,
        null=True,
        blank=True,
        help_text="Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao",
    )

    level1 = models.CharField(
        _("Level 1"),
        choices=choices.thematic_level1,
        max_length=255,
        null=True,
        blank=True,
        help_text="Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao",
    )

    level2 = models.CharField(
        _("Level 2"),
        choices=choices.thematic_level2,
        max_length=255,
        null=True,
        blank=True,
        help_text="Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao",
    )

    autocomplete_search_field = "level0"

    class Meta:
        verbose_name = _("Thematic Area")
        verbose_name_plural = _("Thematic Areas")

    def __unicode__(self):
        return "%s | %s | %s" % (
            self.level0,
            self.level1,
            self.level2,
        )

    def __str__(self):
        return "%s | %s | %s" % (
            self.level0,
            self.level1,
            self.level2,
        )

    def autocomplete_label(self):
        return str(self)

    @property
    def data(self):
        return {
            "thematic_area__level_0": self.level0,
            "thematic_area__level_1": self.level1,
            "thematic_area__level_2": self.level2,
        }

    @classmethod
    def get_or_create(cls, level0, level1, level2, user):
        if ThematicArea.objects.filter(
            level0=level0, level1=level1, level2=level2
        ).exists():
            return ThematicArea.objects.get(level0=level0, level1=level1, level2=level2)
        else:
            the_area = ThematicArea()
            the_area.level0 = level0
            the_area.level1 = level1
            the_area.level2 = level2
            the_area.creator = user
            the_area.save()

        return the_area

    @classmethod
    def parameters_for_values(cls, prefix, level0, level1):
        params = []
        if level0:
            params += [f"{prefix}__level0"]
        if level1:
            params += [f"{prefix}__level1"]
        return params

    @classmethod
    def values(cls, selected_attributes=None):
        selected_attributes = selected_attributes or ["level1"]
        return (
            cls.objects.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        )

    base_form_class = ThematicAreaForm


class Practice(CommonControlField):
    """
    Represent Practices

    Fields:
        name
        code
    """

    name = models.CharField(
        _("Name of the pratice"), blank=True, null=True, max_length=255
    )
    code = models.CharField(
        _("Code of the pratice"), blank=True, null=True, max_length=4
    )

    class Meta:
        verbose_name = _("Practice")
        verbose_name_plural = _("Practices")

    def __unicode__(self):
        return "%s" % (self.name,)

    def __str__(self):
        return "%s" % (self.name,)

    @property
    def data(self):
        return {"practice__name": self.name, "practice__code": self.code}

    @classmethod
    def parameters_for_values(cls, prefix):
        return [
            f"{prefix}__name",
        ]

    @classmethod
    def values(cls, selected_attributes=None):
        selected_attributes = selected_attributes or ["name", "code"]
        return (
            cls.objects.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        )

    base_form_class = PracticeForm


class Action(CommonControlField):
    """
    Represent Action

    Fields:
        name
        code
    """

    name = models.CharField(
        _("Name of the action"), blank=True, null=True, max_length=255
    )
    code = models.CharField(
        _("Code of the action"), blank=True, null=True, max_length=4
    )

    class Meta:
        verbose_name = _("Action")
        verbose_name_plural = _("Actions")

    def __unicode__(self):
        return "%s" % (self.name,)

    def __str__(self):
        return "%s" % (self.name,)

    @property
    def data(self):
        return {"action__name": self.name, "action__code": self.code}

    @classmethod
    def parameters_for_values(cls, prefix):
        return [
            f"{prefix}__name",
        ]

    @classmethod
    def values(cls, selected_attributes=None):
        selected_attributes = selected_attributes or ["code", "name"]
        return (
            cls.objects.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        )

    base_form_class = ActionForm


class ActionAndPractice(models.Model):
    action = models.ForeignKey(
        Action,
        verbose_name=_("Action"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    classification = models.CharField(
        _("Classification"),
        choices=choices.classification,
        max_length=255,
        null=True,
        blank=True,
    )
    practice = models.ForeignKey(
        Practice,
        verbose_name=_("Practice"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def __unicode__(self):
        return "%s" % (self.classification,)

    def __str__(self):
        return "%s" % (self.classification,)

    class Meta:
        indexes = [
            models.Index(fields=["practice"]),
            models.Index(fields=["action"]),
            models.Index(fields=["classification"]),
        ]

    @classmethod
    def get_or_create(cls, action, classification, practice):
        try:
            return ActionAndPractice.objects.get(
                action=action,
                practice=practice,
                classification=classification,
            )
        except ActionAndPractice.DoesNotExist:
            obj = ActionAndPractice()
            obj.action = action
            obj.practice = practice
            obj.classification = classification
            obj.save()
            return obj
        except ActionAndPractice.MultipleObjectsReturned:
            return ActionAndPractice.objects.filter(
                action=action,
                practice=practice,
                classification=classification,
            ).first()

    @property
    def code(self):
        items = (
            self.action and self.action.code,
            self.classification and slugify(self.classification) or "",
            self.practice and self.practice.code or "",
        )
        return slugify("_".join(items)).upper()
