import os

from django.db import models
from django.utils.translation import gettext as _
from .permission_helper import MUST_BE_MODERATE
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel, HelpPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from institution.models import Institution
from usefulmodels.models import Action, Practice, ThematicArea

from . import choices
from .forms import InfrastructureDirectoryFileForm, InfrastructureDirectoryForm


def get_default_action():
    try:
        return Action.objects.get(name__icontains="infra")
    except Action.DoesNotExist:
        return None


class InfrastructureDirectory(CommonControlField):
    class Meta:
        verbose_name_plural = _("Infraestructure Directory")
        permissions = (
            (MUST_BE_MODERATE, _("Must be moderated")),
        )

    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    link = models.URLField(_("Link"), null=False, blank=False)
    description = models.TextField(
        _("Description"), max_length=1000, null=True, blank=True
    )

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
            "Portais, plataformas, servidores, repositórios e serviços brasileiros que operam em acesso aberto objetos de comunicação de comunicação de pesquisas, recursos de apoio e resultantes de pesquisas e em acesso aberto."
        ),
        FieldPanel("title"),
        FieldPanel("link"),
        FieldPanel("source"),
        FieldPanel("description"),
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

    @property
    def data(self):
        d = {
            "infrastructure__title": self.title,
            "infrastructure__link": self.link,
            "infrastructure__description": self.description,
            "infrastructure__classification": self.classification,
            "infrastructure__keywords": [keyword for keyword in self.keywords.names()],
            "infrastructure__record_status": self.record_status,
            "infrastructure__source": self.source,
        }

        if self.institutions:
            inst = []
            for institution in self.institutions.iterator():
                inst.append(institution.data)
            d.update({"infrastructure__institutions": inst})

        if self.thematic_areas:
            area = []
            for thematic_area in self.thematic_areas.iterator():
                area.append(thematic_area.data)
            d.update({"infrastructure__thematic_areas": area})

        if self.practice:
            d.update(self.practice.data)

        if self.action:
            d.update(self.action.data)

        return d

    base_form_class = InfrastructureDirectoryForm


class InfrastructureDirectoryFile(CommonControlField):
    class Meta:
        verbose_name_plural = _("Infraestructure Directory Upload")

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
    base_form_class = InfrastructureDirectoryFileForm
