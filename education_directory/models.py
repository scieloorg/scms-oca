import os

from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.edit_handlers import FieldPanel, HelpPanel
from wagtail.documents.edit_handlers import DocumentChooserPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from institution.models import Institution
from location.models import Location
from usefulmodels.models import Practice, ThematicArea, Action

from .forms import EducationDirectoryFileForm, EducationDirectoryForm

from . import choices


def get_default_action():
    try:
        return Action.objects.get(name__icontains="educa")
    except Action.DoesNotExist:
        return None


class EducationDirectory(CommonControlField):
    class Meta:
        verbose_name_plural = _('Education Directory')

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
    institutions = models.ManyToManyField(Institution, verbose_name=_("Institution"), blank=True)
    thematic_areas = models.ManyToManyField(ThematicArea, verbose_name=_("Thematic Area"), blank=True)

    practice = models.ForeignKey(Practice, verbose_name=_("Practice"),
                                null=True, blank=True, on_delete=models.SET_NULL)
    action = models.ForeignKey(
        Action,
        verbose_name=_("Action"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        default=get_default_action,
    )

    classification = models.CharField(_("Classification"), choices=choices.classification,
                                      max_length=255, null=True, blank=True)

    keywords = TaggableManager(_("Keywords"), blank=True)

    attendance = models.CharField(_("Attendance"), choices=choices.attendance_type,
                                  max_length=255, null=True, blank=True)

    record_status = models.CharField(_("Record status"), choices=choices.status,
                                      max_length=255, null=True, blank=True)

    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)

    panels = [
        HelpPanel('Cursos livres, disciplinas de graduação e pós-graduação ministrados por instituições brasileiras – presenciais ou EAD- para promover a adoção dos princípios e práticas de ciência aberta por todos os envolvidos no processo de pesquisa.'),

        FieldPanel('title'),
        FieldPanel('link'),
        FieldPanel('source'),

        FieldPanel('description'),
        AutocompletePanel('institutions'),

        FieldPanel('start_date'),
        FieldPanel('end_date'),
        FieldPanel('start_time'),
        FieldPanel('end_time'),

        AutocompletePanel('locations'),

        AutocompletePanel('thematic_areas'),
        FieldPanel('keywords'),
        FieldPanel('classification'),
        FieldPanel('practice'),

        FieldPanel('attendance'),
        FieldPanel('record_status'),
    ]

    def __unicode__(self):
        return u'%s' % self.title

    def __str__(self):
        return u'%s' % self.title

    @property
    def data(self):
        d = {
            "education__title": self.title,
            "education__link": self.link,
            "education__description": self.description,
            "education__start_date": self.start_date.isoformat(),
            "education__end_date": self.end_date.isoformat(),
            "education__start_time": self.start_time.isoformat(),
            "education__end_time": self.end_time.isoformat(),
            "education__classification": self.classification,
            "education__keywords": [keyword for keyword in self.keywords.names()],
            "education__attendance": self.attendance,
            "education__record_status": self.record_status,
            "education__source": self.source
        }
        if self.locations:
            loc = []
            for location in self.locations.iterator():
                loc.append(location.data)
            d.update({"education__locations": loc})

        if self.institutions:
            inst = []
            for institution in self.institutions.iterator():
                inst.append(institution.data)
            d.update({"education__institutions": inst})

        if self.thematic_areas:
            area = []
            for thematic_area in self.thematic_areas.iterator():
                area.append(thematic_area.data)
            d.update({"education__thematic_areas": area})

        if self.practice:
            d.update(self.practice.data)

        if self.action:
            d.update(self.action.data)

        return d

    base_form_class = EducationDirectoryForm


class EducationDirectoryFile(CommonControlField):
    class Meta:
        verbose_name_plural = _('Education Directory Upload')

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
    base_form_class = EducationDirectoryFileForm
