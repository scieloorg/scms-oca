from django.db import models
from core.models import CommonControlField
from django.utils.translation import gettext as _

from usefulmodels.models import City, State, Country


class Institution(CommonControlField):
    name = models.CharField(_("Title"), max_length=255, null=False, blank=False)

    city = models.ForeignKey(City, verbose_name=_("City"), on_delete=models.CASCADE,
                             null=False, blank=False)
    state = models.ForeignKey(State, verbose_name=_("State"), on_delete=models.CASCADE,
                              null=False, blank=False)
    country = models.ForeignKey(Country, verbose_name=_("Country"), on_delete=models.CASCADE,
                                null=False, blank=False)
