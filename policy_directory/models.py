import os

from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel, HelpPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from institution.models import Institution
from usefulmodels.models import Action, Practice, ThematicArea

from . import choices
from .forms import PolicyDirectoryFileForm, PolicyDirectoryForm
from .permission_helper import MUST_BE_MODERATE


def get_default_action():
    try:
        return Action.objects.get(name__icontains="políticas")
    except Action.DoesNotExist:
        return None


class PolicyDirectory(CommonControlField):
    class Meta:
        verbose_name_plural = _("Policy Directory")
        permissions = ((MUST_BE_MODERATE, _("Must be moderated")),)

    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    link = models.URLField(_("Link"), null=False, blank=False)
    description = models.TextField(
        _("Description"), max_length=1000, null=True, blank=True
    )
    date = models.DateField(_("Date"), max_length=255, null=True, blank=True)

    institutions = models.ManyToManyField(
        Institution, verbose_name=_("Institution"), blank=True
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
            "Documentos de promoção, posicionamentos ou mandatos sobre Ciência Aberta elaborados e publicados por instituições brasileiras, tais como: universidades, sociedades científicas, institutos de pesquisa e agências de fomento."
        ),
        FieldPanel("title"),
        FieldPanel("link"),
        FieldPanel("source"),
        FieldPanel("description"),
        FieldPanel("date"),
        AutocompletePanel("institutions"),
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

    def get_absolute_edit_url(self):
        return f"/policy_directory/policydirectory/edit/{self.id}/"

    @property
    def data(self):
        d = {
            "policy__title": self.title,
            "policy__link": self.link,
            "policy__description": self.description,
            "policy__date": self.date.isoformat(),
            "policy__classification": self.classification,
            "policy__keywords": [keyword for keyword in self.keywords.names()],
            "policy__record_status": self.record_status,
            "policy__source": self.source,
        }
        if self.institutions:
            inst = []
            for institution in self.institutions.iterator():
                inst.append(institution.data)
            d.update({"policy__institutions": inst})

        if self.thematic_areas:
            area = []
            for thematic_area in self.thematic_areas.iterator():
                area.append(thematic_area.data)
            d.update({"policy__thematic_areas": area})

        if self.practice:
            d.update(self.practice.data)

        if self.action:
            d.update(self.action.data)

        return d

    base_form_class = PolicyDirectoryForm


class PolicyDirectoryFile(CommonControlField):
    class Meta:
        verbose_name_plural = _("Policy Directory Upload")

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
    base_form_class = PolicyDirectoryFileForm
