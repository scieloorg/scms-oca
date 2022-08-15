from django.db import models
from django.utils.translation import gettext as _
from core.models import CommonControlField
from usefulmodels.forms import CityForm, CountryForm, StateForm


class City(CommonControlField):
    """
    Represent a list of cities

    Fields:
        name
    """

    name = models.CharField(_("Name of the city"), blank=True, null=True, max_length=255)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

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

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

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

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    base_form_class = CountryForm

