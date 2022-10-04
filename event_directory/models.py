import os

from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.edit_handlers import FieldPanel, HelpPanel
from wagtail.documents.edit_handlers import DocumentChooserPanel

from core.models import CommonControlField
from core_oca.models import CommonFields

from location.models import Location

from . import choices
from .forms import EventDirectoryFileForm, EventDirectoryForm


class EventDirectory(CommonFields):
    class Meta:
        verbose_name_plural = _('EventDirectory Directory')

    locations = models.ManyToManyField(Location, verbose_name=_("Location"),  blank=True)

    classification = models.CharField(_("Classification"), choices=choices.classification,
                                      max_length=255, null=True, blank=True)

    attendance = models.CharField(_("Attendance"), choices=choices.attendance_type, max_length=255, null=True, blank=True)

    panels = [
        HelpPanel('Encontros, congressos, workshops, seminários realizados no Brasil (presenciais, virtuais ou híbridos) cujo tema principal seja a promoção da Ciência Aberta'),
        FieldPanel('title'),
        FieldPanel('link'),
        FieldPanel('source'),

        FieldPanel('description'),
        FieldPanel('institutions', heading=_("Organization")),

        FieldPanel('start_date'),
        FieldPanel('end_date'),
        FieldPanel('start_time'),
        FieldPanel('end_time'),

        FieldPanel('attendance'),
        FieldPanel('locations'),

        FieldPanel('thematic_areas'),
        FieldPanel('keywords'),
        FieldPanel('classification'),
        FieldPanel('practice'),

        FieldPanel('record_status'),
    ]

    def __unicode__(self):
        return u'%s' % self.title

    def __str__(self):
        return u'%s' % self.title

    base_form_class = EventDirectoryForm


class EventDirectoryFile(CommonControlField):
    class Meta:
        verbose_name_plural = _('EventDirectory Directory Upload')

    attachment = models.ForeignKey(
        'wagtaildocs.Document',
        verbose_name=_("Attachement"),
        null=True, blank=False,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True,
                                   null=True)
    line_count = models.IntegerField(_("Number of lines"), default=0,
                                     blank=True, null=True)

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [
        DocumentChooserPanel('attachment')
    ]
    base_form_class = EventDirectoryFileForm
