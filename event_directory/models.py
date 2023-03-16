import os

from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel, HelpPanel

from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from institution.models import Institution
from location.models import Location
from usefulmodels.models import ThematicArea, Practice, Action

from . import choices
from .forms import EventDirectoryFileForm, EventDirectoryForm


def get_default_action():
    try:
        return Action.objects.get(name__icontains="disseminação")
    except Action.DoesNotExist:
        return None


class EventDirectory(CommonControlField):
    class Meta:
        verbose_name_plural = _("EventDirectory Directory")

    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    link = models.URLField(_("Link"), null=False, blank=False)
    description = models.TextField(
        _("Description"), max_length=1000, null=True, blank=True
    )
    start_date = models.DateField(
        _("Start Date"), max_length=255, null=True, blank=True
    )
    end_date = models.DateField(_("End Date"), max_length=255, null=True, blank=True)
    start_time = models.TimeField(
        _("Start Time"), max_length=255, null=True, blank=True
    )
    end_time = models.TimeField(_("End Time"), max_length=255, null=True, blank=True)

    locations = models.ManyToManyField(Location, verbose_name=_("Location"), blank=True)
    organization = models.ManyToManyField(
        Institution,
        verbose_name=_("Instituição"),
        blank=True,
        help_text=_("Instituições responsáveis pela organização do evento."),
    )
    thematic_areas = models.ManyToManyField(
        ThematicArea, verbose_name=_("Thematic Area"), blank=True
    )

    practice = models.ForeignKey(
        Practice,
        verbose_name=_("Practice"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    action = models.ForeignKey(
        Action,
        verbose_name=_("Action"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        default=get_default_action,
    )

    classification = models.CharField(
        _("Classification"),
        choices=choices.classification,
        max_length=255,
        null=True,
        blank=True,
    )
    keywords = TaggableManager(_("Keywords"), blank=True)

    attendance = models.CharField(
        _("Attendance"),
        choices=choices.attendance_type,
        max_length=255,
        null=True,
        blank=True,
    )

    record_status = models.CharField(
        _("Record status"),
        choices=choices.status,
        max_length=255,
        null=True,
        blank=True,
    )
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)

    panels = [
        HelpPanel(
            "Encontros, congressos, workshops, seminários realizados no Brasil (presenciais, virtuais ou híbridos) cujo tema principal seja a promoção da Ciência Aberta"
        ),
        FieldPanel("title"),
        FieldPanel("link"),
        FieldPanel("source"),
        FieldPanel("description"),
        AutocompletePanel("organization"),
        FieldPanel("start_date"),
        FieldPanel("end_date"),
        FieldPanel("start_time"),
        FieldPanel("end_time"),
        FieldPanel("attendance"),
        AutocompletePanel("locations"),
        AutocompletePanel("thematic_areas"),
        FieldPanel("keywords"),
        FieldPanel("classification"),
        FieldPanel("practice"),
        FieldPanel("record_status"),
    ]

    def __unicode__(self):
        return "%s" % self.title

    def __str__(self):
        return "%s" % self.title

    @property
    def data(self):
        d = {
            "event__title": self.title,
            "event__link": self.link,
            "event__description": self.description,
            "event__start_date": self.start_date.isoformat(),
            "event__end_date": self.end_date.isoformat(),
            "event__start_time": self.start_time.isoformat(),
            "event__end_time": self.end_time.isoformat(),
            "event__classification": self.classification,
            "event__keywords": [keyword for keyword in self.keywords.names()],
            "event__attendance": self.attendance,
            "event__record_status": self.record_status,
            "event__source": self.source,
        }
        if self.locations:
            loc = []
            for location in self.locations.iterator():
                loc.append(location.data)
            d.update({"event__locations": loc})

        if self.organization:
            org_list = []
            for org in self.organization.iterator():
                org_list.append(org.data)
            d.update({"event__organization": org_list})

        if self.thematic_areas:
            area = []
            for thematic_area in self.thematic_areas.iterator():
                area.append(thematic_area.data)
            d.update({"event__thematic_areas": area})

        if self.practice:
            d.update(self.practice.data)

        if self.action:
            d.update(self.action.data)

        return d

    base_form_class = EventDirectoryForm


class EventDirectoryFile(CommonControlField):
    class Meta:
        verbose_name_plural = _("EventDirectory Directory Upload")

    attachment = models.ForeignKey(
        "wagtaildocs.Document",
        verbose_name=_("Attachement"),
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True, null=True)
    line_count = models.IntegerField(
        _("Number of lines"), default=0, blank=True, null=True
    )

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [FieldPanel("attachment")]
    base_form_class = EventDirectoryFileForm
