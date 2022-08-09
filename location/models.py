from django.db import models
from core.models import CommonControlField
from django.utils.translation import gettext as _

from usefulmodels.models import City, State, Country

from . import choices


class Location(CommonControlField):
    name = models.CharField(_("Name"), max_length=255, null=True, blank=True)

    region = models.CharField(_("Region"), choices=choices.regions, max_length=255, null=True, blank=True)

    city = models.ForeignKey(City, verbose_name=_("City"), on_delete=models.CASCADE,
                             null=True, blank=True)
    state = models.ForeignKey(State, verbose_name=_("State"), on_delete=models.CASCADE,
                              null=True, blank=True)
    country = models.ForeignKey(Country, verbose_name=_("Country"), on_delete=models.CASCADE,
                                null=True, blank=True)
