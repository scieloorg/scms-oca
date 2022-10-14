from django.db import models
from django.utils.translation import gettext as _
from core.models import CommonControlField
from usefulmodels.forms import (CityForm, CountryForm, StateForm, ThematicAreaForm,
                                PracticeForm, ActionForm)

from . import choices

class City(CommonControlField):
    """
    Represent a list of cities

    Fields:
        name
    """

    name = models.CharField(_("Name of the city"), blank=True, null=True, max_length=255)

    autocomplete_search_field = 'name'

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __unicode__(self):
        return u'%s' % self.name

    def __str__(self):
        return u'%s' % self.name

    def autocomplete_label(self):
        return str(self)

    @classmethod
    def get_or_create(cls, user, name):

        if cls.objects.filter(name__exact=name).exists():
            return cls.objects.get(name__exact=name)
        else:
            city = City()
            city.name = name
            city.creator = user
            city.save()

        return city

    base_form_class = CityForm


class State(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        acronym
    """

    name = models.CharField(_("Name of the state"), blank=True, null=True, max_length=255)
    acronym = models.CharField(_("Acronym to the state"), blank=True, null=True, max_length=255)
    region = models.CharField(_("Region"), choices=choices.regions, max_length=255, null=True, blank=True)

    autocomplete_search_field = 'name'

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")

    def __unicode__(self):
        return u'%s' % self.name

    def __str__(self):
        return u'%s' % self.name

    def autocomplete_label(self):
        return str(self)

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

    base_form_class = StateForm


class Country(CommonControlField):
    """
    Represent the list of Countries

    Fields:
        name
        acronym
    """

    name = models.CharField(_("Name of the Country"), blank=True, null=True, max_length=255)
    acronym = models.CharField(_("Acronym to the Country"), blank=True, null=True, max_length=255)

    autocomplete_search_field = 'name'

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    def __unicode__(self):
        return u'%s' % self.name

    def __str__(self):
        return u'%s' % self.name

    def autocomplete_label(self):
        return str(self)

    @classmethod
    def get_or_create(cls, user, name=None, acronym=None):

        if name:
            if cls.objects.filter(name__exact=name).exists():
                return cls.objects.get(name__exact=name)

        if acronym:
            if cls.objects.filter(acronym__exact=acronym).exists():
                return cls.objects.get(acronym__exact=acronym)

        country = Country()
        country.name = name
        country.acronym = acronym
        country.creator = user
        country.save()

        return country

    base_form_class = CountryForm


class ThematicArea(CommonControlField):
    """
    Represent the thematic areas wit 3 levels.

    Fields:
        level 0
        level 1
        level 2
    """

    level0 = models.CharField(_("Level 0"), choices=choices.thematic_level0,
                              max_length=255, null=True, blank=True, help_text="Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao")

    level1 = models.CharField(_("Level 1"), choices=choices.thematic_level1,
                              max_length=255, null=True, blank=True, help_text="Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao")

    level2 = models.CharField(_("Level 2"), choices=choices.thematic_level2,
                              max_length=255, null=True, blank=True, help_text="Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao")

    autocomplete_search_field = 'level0'

    class Meta:
        verbose_name = _("Thematic Area")
        verbose_name_plural = _("Thematic Areas")

    def __unicode__(self):
        return u'%s | %s | %s' % (self.level0, self.level1, self.level2, )

    def __str__(self):
        return u'%s | %s | %s' % (self.level0, self.level1, self.level2, )

    def autocomplete_label(self):
        return str(self)

    @classmethod
    def get_or_create(cls, level0, level1, level2, user):

        if ThematicArea.objects.filter(level0=level0, level1=level1, level2=level2).exists():
            return ThematicArea.objects.get(level0=level0, level1=level1, level2=level2)
        else:
            the_area = ThematicArea()
            the_area.level0 = level0
            the_area.level1 = level1
            the_area.level2 = level2
            the_area.creator = user
            the_area.save()

        return the_area


    base_form_class = ThematicAreaForm


class Practice(CommonControlField):
    """
    Represent Practices

    Fields:
        name
        code
    """
    name = models.CharField(_("Name of the pratice"), blank=True, null=True, max_length=255)
    code = models.CharField(_("Code of the pratice"), blank=True, null=True, max_length=4)

    class Meta:
        verbose_name = _("Practice")
        verbose_name_plural = _("Practices")

    def __unicode__(self):
        return u'%s' % (self.name, )

    def __str__(self):
        return u'%s' % (self.name, )

    base_form_class = PracticeForm


class Action(CommonControlField):
    """
    Represent Action

    Fields:
        name
        code
    """
    name = models.CharField(_("Name of the action"), blank=True, null=True, max_length=255)
    code = models.CharField(_("Code of the action"), blank=True, null=True, max_length=4)

    class Meta:
        verbose_name = _("Action")
        verbose_name_plural = _("Actions")

    def __unicode__(self):
        return u'%s' % (self.name, )

    def __str__(self):
        return u'%s' % (self.name, )

    base_form_class = ActionForm
