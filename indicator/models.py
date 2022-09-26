from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel

from core.models import CommonControlField

from . import choices
from .forms import IndicatorDirectoryForm
from usefulmodels.models import Action, Practice, ThematicArea
from institution.models import Institution
from location.models import Location

class Indicator(CommonControlField):
    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    description = models.TextField(_("Description"), max_length=1000,
                                   null=True, blank=True)
    versioning = models.ForeignKey("Versioning", verbose_name=_("Versioning"), on_delete=models.SET_NULL,
                                   max_length=255, null=True, blank=True)
    action = models.ForeignKey(Action, verbose_name=_("Action"), null=True, blank=True, on_delete=models.SET_NULL)
    classification = models.CharField(_("Classification"), choices=choices.classification,
                                      max_length=255, null=True, blank=True)
    practice = models.ForeignKey(Practice, verbose_name=_("Practice"),
                                 null=True, blank=True, on_delete=models.SET_NULL)
    thematic_areas = models.ManyToManyField(ThematicArea, verbose_name=_("Thematic Area"), blank=True)
    institutions = models.ManyToManyField(Institution, verbose_name=_("Institution"), blank=True)
    locations = models.ManyToManyField(Location, verbose_name=_("Location"),  blank=True)
    start_date = models.DateField(_("Start Date"), max_length=255, null=True, blank=True)
    end_date = models.DateField(_("End Date"), max_length=255, null=True, blank=True)
    link = models.URLField(_("Link"), null=False, blank=False)
    file_csv = models.FileField(_("CSV File"), null=True, blank=True)
    file_json = models.JSONField(_("JSON File"), null=True, blank=True)
    keywords = TaggableManager(_("Keywords"), blank=True)
    record_status = models.CharField(_("Record status"), choices=choices.status,
                                     max_length=255, null=True, blank=True)
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)


    class Meta:
        indexes = [
            models.Index(fields=['title', ]),
            models.Index(fields=['action', ]),
            models.Index(fields=['practice', ]),
            models.Index(fields=['start_date', ]),
            models.Index(fields=['end_date', ]),
        ]

    # panels = [
    #     FieldPanel('name'),
    #     FieldPanel('post'),
    #     FieldPanel('versioning'),
    #     FieldPanel('action'),
    #     FieldPanel('practice'),
    #     FieldPanel('thematic_area'),
    #     FieldPanel('institution'),
    #     FieldPanel('location'),
    #     FieldPanel('start_date'),
    #     FieldPanel('end_date'),
    #     FieldPanel('file_csv'),
    #     FieldPanel('file_json'),
    # ]

    def __unicode__(self):
        return u'%s - %s' % (self.identifier, self.name)

    def __str__(self):
        return u'%s - %s' % (self.identifier, self.name)

    base_form_class = IndicatorDirectoryForm


class Versioning(CommonControlField):
    previous_record = models.ForeignKey(Indicator, verbose_name=_("Previous Record"), related_name="predecessor_register",
                                        on_delete=models.SET_NULL,
                                        max_length=255, null=True, blank=True)
    posterior_record = models.ForeignKey(Indicator, verbose_name=_("Posterior Record"), related_name="successor_register",
                                        on_delete=models.SET_NULL,
                                        max_length=255, null=True, blank=True)

    panels = [
        FieldPanel('previous_record'),
        FieldPanel('posterior_record'),
    ]

    s = ''
    if previous_record:
        s += str(previous_record) + ' - '
    if posterior_record:
        s += str(posterior_record)

    def __unicode__(self):
        return s

    def __str__(self):
        return s
