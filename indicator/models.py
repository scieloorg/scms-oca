from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel

from core.models import CommonControlField

from . import choices
from .forms import IndicatorDirectoryForm
from usefulmodels.models import Action, Practice, ThematicArea
from institution.models import Institution
from location.models import Location

class Indicator(CommonControlField):
    name = models.CharField(_("Name"), max_length=255, null=True, blank=True)
    post = models.ForeignKey("Post", verbose_name=_("Post"), on_delete=models.SET_NULL,
                             max_length=255, null=True, blank=True)
    versioning = models.ForeignKey("Versioning", verbose_name=_("Versioning"), on_delete=models.SET_NULL,
                                   max_length=255, null=True, blank=True)
    action = models.ForeignKey(Action, verbose_name=_("Action"), on_delete=models.SET_NULL,
                               max_length=255, null=True, blank=True)
    practice = models.ForeignKey(Practice, verbose_name=_("Practice"), on_delete=models.SET_NULL,
                                 max_length=255, null=True, blank=True)
    thematic_area = models.ForeignKey(ThematicArea, verbose_name=_("Thematic Area"), on_delete=models.SET_NULL,
                                      max_length=255, null=True, blank=True)
    institutional_context = models.ForeignKey(Institution, verbose_name=_("Institutional context"),
                                              on_delete=models.SET_NULL, max_length=255, null=True, blank=True)
    geographic_context = models.ForeignKey(Location, verbose_name=_("Geographic context"), on_delete=models.SET_NULL,
                                           max_length=255, null=True, blank=True)
    chronology = models.DateField(_("Date"), max_length=255, null=True, blank=True)
    file_csv = models.FileField(_("CSV File"), null=True, blank=True)
    file_json = models.JSONField(_("JSON File"), null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['action', ]),
            models.Index(fields=['practice', ]),
        ]

    panels = [
        FieldPanel('name'),
        FieldPanel('post'),
        FieldPanel('versioning'),
        FieldPanel('action'),
        FieldPanel('practice'),
        FieldPanel('thematic_area'),
        FieldPanel('institutional_context'),
        FieldPanel('geographic_context'),
        FieldPanel('chronology'),
        FieldPanel('file_csv'),
        FieldPanel('file_json'),
    ]

    def __unicode__(self):
        return u'%s - %s' % (self.identifier, self.name)

    def __str__(self):
        return u'%s - %s' % (self.identifier, self.name)

    base_form_class = IndicatorDirectoryForm


class Post(CommonControlField):
    post_date = models.DateField(_("Post Date"), max_length=255, null=True, blank=True)
    authorship_post = models.CharField(_("Authorship of the Post"), max_length=255, null=True, blank=True)

    panels = [
        FieldPanel('post_date'),
        FieldPanel('authorship_post'),
    ]

    def __unicode__(self):
        return u'%s - %s' % (self.post_date, self.authorship_post)

    def __str__(self):
        return u'%s - %s' % (self.post_date, self.authorship_post)


class Versioning(CommonControlField):
    record_status = models.CharField(_("Record status"), choices=choices.status, max_length=255, null=True, blank=True)
    previous_record = models.ForeignKey(Indicator, verbose_name=_("Previous Record"), related_name="predecessor_register",
                                        on_delete=models.SET_NULL,
                                        max_length=255, null=True, blank=True)
    posterior_record = models.ForeignKey(Indicator, verbose_name=_("Posterior Record"), related_name="successor_register",
                                        on_delete=models.SET_NULL,
                                        max_length=255, null=True, blank=True)

    panels = [
        FieldPanel('record_status'),
        FieldPanel('previous_record'),
        FieldPanel('posterior_record'),
    ]

    s = ''
    if record_status:
        s += str(record_status) + ' - '
    if previous_record:
        s += str(previous_record) + ' - '
    if posterior_record:
        s += str(posterior_record)

    def __unicode__(self):
        return s

    def __str__(self):
        return s
