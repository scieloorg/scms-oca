from django.db import models
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from wagtail.core.models import Orderable

from core.models import CommonControlField
from usefulmodels.models import City, Country, State

from . import choices
from .forms import LocationForm


class Location(CommonControlField):

    city = models.ForeignKey(City, verbose_name=_("City"), on_delete=models.CASCADE,
                             null=True, blank=True)
    state = models.ForeignKey(State, verbose_name=_("State"), on_delete=models.CASCADE,
                              null=True, blank=True)
    country = models.ForeignKey(Country, verbose_name=_("Country"), on_delete=models.CASCADE,
                                null=True, blank=True)

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")

    def __unicode__(self):
        return u'%s: %s | %s: %s | %s: %s' % (_('Country'), self.country, _('State'),  self.state, _('City'), self.city, )

    def __str__(self):
        return u'%s: %s | %s: %s | %s: %s' % (_('Country'), self.country, _('State'),  self.state, _('City'), self.city, )

    @classmethod
    def get_or_create(cls, user, location_country, location_state,
                      location_city):

        # check if exists the location
        if cls.objects.filter(country=location_country, state=location_state, city=location_city).exists():
            return cls.objects.get(
                country=location_country, state=location_state, city=location_city)
        else:
            location = Location()
            if location_country:
                location.country = location_country
            if location_state:
                location.state = location_state
            if location_city:
                location.city = location_city
            location.creator = user
            location.save()

        return location


    base_form_class = LocationForm
