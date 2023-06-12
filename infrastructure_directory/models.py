import os

from django.db import models
from django.conf import settings
from django.utils.translation import gettext as _
from django.db.models import Count
from .permission_helper import MUST_BE_MODERATE
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel, HelpPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from institution.models import Institution
from usefulmodels.models import Action, Practice, ThematicArea, State

from . import choices
from .forms import InfrastructureDirectoryFileForm, InfrastructureDirectoryForm
from core import help_fields


def get_default_action():
    try:
        return Action.objects.get(name__icontains="infra")
    except Action.DoesNotExist:
        return None


class InfrastructureDirectory(CommonControlField):
    class Meta:
        verbose_name_plural = _("Infrastructure Data")
        verbose_name = _("Infrastructure Data")
        permissions = (
            (MUST_BE_MODERATE, _("Must be moderated")),
            ("can_edit_title", _("Can edit title")),
            ("can_edit_link", _("Can edit link")),
            ("can_edit_description", _("Can edit description")),
            ("can_edit_locations", _("Can edit locations")),
            ("can_edit_institutions", _("Can edit institutions")),
            ("can_edit_thematic_areas", _("Can edit thematic_areas")),
            ("can_edit_practice", _("Can edit practice")),
            ("can_edit_action", _("Can edit action")),
            ("can_edit_classification", _("Can edit classification")),
            ("can_edit_keywords", _("Can edit keywords")),
            ("can_edit_record_status", _("Can edit record_status")),
            ("can_edit_source", _("Can edit source")),
            (
                "can_edit_institutional_contribution",
                _("Can edit institutional_contribution"),
            ),
            ("can_edit_notes", _("Can edit notes")),
        )

    title = models.CharField(
        _("Title"),
        max_length=255,
        null=False,
        blank=False,
        help_text=help_fields.DIRECTORY_TITLE_HELP,
    )
    link = models.URLField(
        _("Link"), null=False, blank=False, help_text=help_fields.DIRECTORY_LINK_HELP
    )
    description = models.TextField(
        _("Description"),
        max_length=1000,
        null=True,
        blank=True,
        help_text=help_fields.DIRECTORY_DESCRIPTION_HELP,
    )

    institutions = models.ManyToManyField(
        Institution,
        verbose_name=_("Institution"),
        blank=True,
        help_text=help_fields.DIRECTORY_INSTITUTIONS_HELP,
    )
    thematic_areas = models.ManyToManyField(
        ThematicArea,
        verbose_name=_("Thematic Area"),
        blank=True,
        help_text=help_fields.DIRECTORY_THEMATIC_AREA_HELP,
    )

    practice = models.ForeignKey(
        Practice,
        verbose_name=_("Practice"),
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        help_text=help_fields.DIRECTORY_PRACTICE_HELP,
    )

    action = models.ForeignKey(
        Action,
        verbose_name=_("Action"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        default=get_default_action,
        help_text=help_fields.DIRECTORY_ACTION_HELP,
    )

    classification = models.CharField(
        _("Classification"),
        choices=choices.classification,
        max_length=255,
        null=True,
        blank=True,
        help_text=help_fields.DIRECTORY_CLASSIFICATION_HELP,
    )

    keywords = TaggableManager(
        _("Keywords"), blank=True, help_text=help_fields.DIRECTORY_KEYWORDS_AREA_HELP
    )

    record_status = models.CharField(
        _("Record status"),
        choices=choices.status,
        max_length=255,
        null=True,
        blank=True,
        help_text=help_fields.DIRECTORY_RECORD_STATUS_HELP,
    )

    source = models.CharField(
        _("Source"),
        max_length=255,
        null=True,
        blank=True,
        help_text=help_fields.DIRECTORY_SOURCE_HELP,
    )

    institutional_contribution = models.CharField(
        _("Institutional Contribution"),
        max_length=255,
        default=settings.DIRECTORY_DEFAULT_CONTRIBUTOR,
        help_text=help_fields.DIRECTORY_INSTITUTIONAL_CONTRIBUTION_HELP,
    )

    notes = models.TextField(
        _("Notes"),
        max_length=1000,
        null=True,
        blank=True,
        help_text=help_fields.DIRECTORY_NOTES_HELP,
    )

    panels = [
        HelpPanel(
            "Portais, plataformas, servidores, repositórios e serviços brasileiros que operam em acesso aberto objetos de comunicação de comunicação de pesquisas, recursos de apoio e resultantes de pesquisas e em acesso aberto."
        ),
        FieldPanel("title"),
        FieldPanel("link"),
        FieldPanel("source"),
        FieldPanel("description"),
        FieldPanel("institutional_contribution"),
        AutocompletePanel("institutions"),
        AutocompletePanel("thematic_areas"),
        FieldPanel("keywords"),
        FieldPanel("classification"),
        FieldPanel("practice"),
        FieldPanel("record_status"),
        FieldPanel("notes"),
    ]

    def __unicode__(self):
        return "%s" % self.title

    def __str__(self):
        return "%s" % self.title

    def get_absolute_edit_url(self):
        return f"/infrastructure_directory/infrastructuredirectory/edit/{self.id}/"

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
            "infrastructure__action": self.action,
            "infrastructure__practice": self.practice,
            "infrastructure__institutional_contribution": self.institutional_contribution,
            "infrastructure__notes": self.notes,
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

    @classmethod
    def filter_items_to_generate_indicators(
        cls,
        action__name=None,
        practice__code=None,
        practice__name=None,
        classification=None,
        institution__name=None,
        thematic_area__level0=None,
        thematic_area__level1=None,
        location__state__code=None,
        location__region=None,
    ):
        params = dict(
            action__name=action__name,
            practice__code=practice__code,
            practice__name=practice__name,
            classification=classification,
            institutions__name=institution__name,
            institutions__location__state__acronym=location__state__code,
            institutions__location__region=location__region,
            thematic_areas__level0=thematic_area__level0,
            thematic_areas__level1=thematic_area__level1,
        )
        params = {k: v for k, v in params.items() if v}
        return cls.objects.filter(record_status="PUBLISHED", **params)

    @classmethod
    def parameters_for_values(
        cls,
        by_practice=False,
        by_classification=False,
        by_institution=False,
        by_thematic_area_level0=False,
        by_thematic_area_level1=False,
        by_state=False,
        by_region=False,
    ):
        selected_attributes = Action.parameters_for_values("action")
        if by_classification:
            selected_attributes += ["classification"]
        if by_practice:
            selected_attributes += Practice.parameters_for_values("practice")
        if by_institution:
            selected_attributes += Institution.parameters_for_values("institutions")
        if by_state or by_state or by_region:
            selected_attributes += State.parameters_for_values(
                "institutions__location__state", by_state, by_state, by_region
            )
        if by_thematic_area_level0 or by_thematic_area_level1:
            selected_attributes += ThematicArea.parameters_for_values(
                "thematic_areas", by_thematic_area_level0, by_thematic_area_level1
            )

        return selected_attributes

    @classmethod
    def group(
        cls,
        query_result,
        selected_attributes,
    ):
        return (
            query_result.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by("count")
            .iterator()
        )

    base_form_class = InfrastructureDirectoryForm


class InfrastructureDirectoryFile(CommonControlField):
    class Meta:
        verbose_name_plural = _("Infrastructure Data Upload")
        verbose_name = _("Infrastructure Data Upload")

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
