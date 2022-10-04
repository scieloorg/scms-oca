from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager

from institution.models import Institution
from usefulmodels.models import ThematicArea, Practice, Action
from . import choices


class CommonFields(models.Model):
    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    link = models.URLField(_("Link"), null=True, blank=True)
    description = models.TextField(_("Description"), max_length=1000, null=True, blank=True)
    start_date = models.DateField(_("Start Date"), max_length=255, null=True, blank=True)
    end_date = models.DateField(_("End Date"), max_length=255, null=True, blank=True)
    start_time = models.TimeField(_("Start Time"), max_length=255, null=True, blank=True)
    end_time = models.TimeField(_("End Time"), max_length=255, null=True, blank=True)
    institutions = models.ManyToManyField(Institution, verbose_name=_("Institution"), blank=True)
    thematic_areas = models.ManyToManyField(ThematicArea, verbose_name=_("Thematic Area"), blank=True)
    practice = models.ForeignKey(Practice, verbose_name=_("Practice"), null=True, blank=True, on_delete=models.SET_NULL)
    action = models.ForeignKey(Action, verbose_name=_("Action"), null=True, blank=True, on_delete=models.SET_NULL)
    keywords = TaggableManager(_("Keywords"), blank=True)
    record_status = models.CharField(_("Record status"), choices=choices.status, max_length=255, null=True, blank=True)
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)


    class Meta:
        abstract = True

