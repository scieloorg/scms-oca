import os

from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.edit_handlers import FieldPanel, HelpPanel
from wagtail.documents.edit_handlers import DocumentChooserPanel

from core.models import CommonControlField
from institution.models import Institution
from location.models import Location
from usefulmodels.models import ThematicArea, Practice, Action

from . import choices
from .forms import EventDirectoryFileForm, EventDirectoryForm


class EventDirectory(CommonControlField):
    class Meta:
        verbose_name_plural = _('EventDirectory Directory')

    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    link = models.URLField(_("Link"), null=False, blank=False)
    description = models.TextField(_("Description"), max_length=1000,
                                   null=True, blank=True)
    start_date = models.DateField(_("Start Date"), max_length=255,
                                  null=True, blank=True)
    end_date = models.DateField(_("End Date"), max_length=255,
                                null=True, blank=True)
    start_time = models.TimeField(_("Start Time"), max_length=255,
                                  null=True, blank=True)
    end_time = models.TimeField(_("End Time"), max_length=255,
                                null=True, blank=True)

    locations = models.ManyToManyField(Location, verbose_name=_("Location"),  blank=True)
    organization = models.ManyToManyField(Institution, verbose_name=_(
        "Institution"), blank=True, help_text=_('Instituições responsáveis pela organização do evento.'))
    thematic_areas = models.ManyToManyField(ThematicArea, verbose_name=_("Thematic Area"), blank=True)

    practice = models.ForeignKey(Practice, verbose_name=_("Practice"),
                                null=True, blank=True, on_delete=models.SET_NULL)
    action = models.ForeignKey(Action, verbose_name=_("Action"), null=True, blank=True, on_delete=models.SET_NULL)

    classification = models.CharField(_("Classification"), choices=choices.classification,
                                      max_length=255, null=True, blank=True)
    keywords = TaggableManager(_("Keywords"), blank=True)

    attendence = models.CharField(_("Attendence"), choices=choices.attendance_type, max_length=255, null=True, blank=True)

    record_status = models.CharField(_("Record status"), choices=choices.status,
                                     max_length=255, null=True, blank=True)
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)

    panels = [
        HelpPanel('Encontros, congressos, workshops, seminários realizados no Brasil (presenciais, virtuais ou híbridos) cujo tema principal seja a promoção da Ciência Aberta'),
        FieldPanel('title'),
        FieldPanel('link'),
        FieldPanel('source'),

        FieldPanel('description'),
        FieldPanel('organization'),

        FieldPanel('start_date'),
        FieldPanel('end_date'),
        FieldPanel('start_time'),
        FieldPanel('end_time'),

        FieldPanel('attendence'),
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
