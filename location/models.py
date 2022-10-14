from django.db import models
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from wagtail.core.models import Orderable

from core.models import CommonControlField
from usefulmodels.models import City, Country, State
from wagtailautocomplete.edit_handlers import AutocompletePanel

from . import choices
from .forms import LocationForm


class Location(CommonControlField):

    city = models.ForeignKey(City, verbose_name=_("City"), on_delete=models.CASCADE,
                             null=True, blank=True)
    state = models.ForeignKey(State, verbose_name=_("State"), on_delete=models.CASCADE,
                              null=True, blank=True)
    country = models.ForeignKey(Country, verbose_name=_("Country"), on_delete=models.CASCADE,
                                null=True, blank=True)

    autocomplete_search_field = 'state__name'

    def autocomplete_label(self):
        return str(self)
    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")

    panels = [
        AutocompletePanel('city'),
        AutocompletePanel('state'),
        AutocompletePanel('country'),
    ]

    def __unicode__(self):
        return u'%s: %s | %s: %s | %s: %s' % (_('Country'), self.country, _('State'),  self.state, _('City'), self.city, )

    def __str__(self):
        return u'%s: %s | %s: %s | %s: %s' % (_('Country'), self.country, _('State'),  self.state, _('City'), self.city, )

    @classmethod
    def get_or_create(cls, user, location_country, location_state, location_city):

        # check if exists the location
        if cls.objects.filter(country__name=location_country, state__name=location_state, city__name=location_city).exists():
            return cls.objects.get(
                country__name=location_country, state__name=location_state, city__name=location_city)
        else:
            location = Location()
            if location_country:
                location.country = Country.get_or_create(user, location_country)
            if location_state:
                location.state = State.get_or_create(user, location_state)
            if location_city:
                location.city = City.get_or_create(user, location_city)
            location.creator = user
            location.save()

        return location

    base_form_class = LocationForm
