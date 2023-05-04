import json
import logging
import os
import secrets
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from institution.models import Institution
from location.models import Location
from usefulmodels.models import ActionAndPractice, ThematicArea

from . import choices
from .forms import IndicatorDirectoryForm
from .permission_helper import MUST_BE_MODERATE


class Indicator(CommonControlField):
    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    description = models.TextField(
        _("Description"), max_length=1000, null=True, blank=True
    )

    validity = models.CharField(
        _("Record validity"),
        choices=choices.VALIDITY,
        max_length=255,
        null=True,
        blank=True,
    )
    previous_record = models.ForeignKey(
        "self",
        verbose_name=_("Previous Record"),
        related_name="predecessor_register",
        on_delete=models.SET_NULL,
        max_length=255,
        null=True,
        blank=True,
    )
    posterior_record = models.ForeignKey(
        "self",
        verbose_name=_("Posterior Record"),
        related_name="successor_register",
        on_delete=models.SET_NULL,
        max_length=255,
        null=True,
        blank=True,
    )
    seq = models.IntegerField(_("Sequential number"), null=True, blank=True)

    action_and_practice = models.ForeignKey(
        ActionAndPractice, on_delete=models.SET_NULL, null=True
    )
    thematic_areas = models.ManyToManyField(
        ThematicArea, verbose_name=_("Thematic Area"), blank=True
    )
    institutions = models.ManyToManyField(
        Institution, verbose_name=_("Institution"), blank=True
    )
    locations = models.ManyToManyField(Location, verbose_name=_("Location"), blank=True)
    start_date_year = models.IntegerField(_("Start Date"), null=True, blank=True)
    end_date_year = models.IntegerField(_("End Date"), null=True, blank=True)

    link = models.URLField(_("Link"), null=True, blank=True)
    raw_data = models.FileField(
        _("JSONL Zip File"), null=True, blank=True, max_length=255
    )
    summarized = models.JSONField(_("JSON File"), null=True, blank=True)

    keywords = TaggableManager(_("Keywords"), blank=True)

    record_status = models.CharField(
        _("Record status"),
        choices=choices.status,
        max_length=255,
        null=True,
        blank=True,
    )
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)

    scope = models.CharField(
        _("Scope"), choices=choices.SCOPE, max_length=20, null=True
    )
    measurement = models.CharField(
        _("Measurement"), choices=choices.MEASUREMENT_TYPE, max_length=25, null=True
    )
    code = models.CharField(_("Code"), max_length=555, null=False, blank=False)

    object_name = models.CharField(
        _("Observation"), max_length=255, null=True, blank=False
    )
    category = models.CharField(_("Categoria"), max_length=255, null=True, blank=False)
    context = models.CharField(_("Contexto"), max_length=255, null=True, blank=False)
    slug = models.SlugField(unique=True, null=True, max_length=64)

    link_to_graphic = models.URLField(_("Link to graphic"), null=True, blank=True)

    link_to_data = models.URLField(_("Link to the data"), null=True, blank=True)

    def save(self, *args, **kwargs):
        # ensure we always have the slug.
        if not self.slug:
            self.slug = secrets.token_urlsafe(48)
        return super().save(*args, **kwargs)

    def get_absolute_edit_url(self):
        return f"/indicator/indicator/edit/{self.id}/"

    @property
    def header(self):
        link = "https://ocabr.org/search/indicator/{}/detail/".format(
            self.id,
        )
        d = dict(
            title=self.title,
            description=self.description,
            validity=self.validity,
            version=self.seq,
            link=link,
            source="OCABr",
            updated=self.updated.isoformat(),
            contributors=["SciELO"],
            action=self.action_and_practice and self.action_and_practice.action.name,
            practice=self.action_and_practice and self.action_and_practice.action.name,
            qualification=self.action_and_practice
            and self.action_and_practice.classification,
            license="CC-BY",
        )
        indicator = {}
        indicator["indicator"] = {k: v for k, v in d.items() if v}
        return indicator

    def save_raw_data(self, items):
        with TemporaryDirectory() as tmpdirname:
            temp_zip_file_path = os.path.join(tmpdirname, self.filename + ".zip")
            file_path = os.path.join(settings.MEDIA_ROOT, self.filename + ".zip")
            logging.info("TemporaryDirectory %s" % tmpdirname)
            logging.info("file_path %s" % file_path)
            with ZipFile(temp_zip_file_path, "w") as zf:
                zf.writestr(
                    self.filename + ".jsonl", "".join(self._raw_data_rows(items))
                )
            shutil.move(temp_zip_file_path, file_path)
            logging.info("existe file_path? %s" % os.path.isfile(file_path))
        self.raw_data.name = file_path
        self.save()

    def _raw_data_rows(self, items):
        for item in items:
            try:
                data = item.data
            except:
                data = {"teste": "teste"}
            else:
                data.update(self.header)
                yield f"{json.dumps(data)}\n"

    @property
    def disclaimer(self):

        if self.updated_by:
            return (
                settings.CONTENT_DISCLAIMER_MESSAGE
                if not self.updated_by.is_staff and self.record_status == "PUBLISHED"
                else None
            )
        
        if self.creator: 
            return (
                settings.CONTENT_DISCLAIMER_MESSAGE
                if not self.creator.is_staff and self.record_status == "PUBLISHED"
                else None
            )   

    class Meta:
        permissions = (
            (MUST_BE_MODERATE, _("Must be moderated")),
            ("can_edit_record_status", _("Can edit record_status")),
            ("can_edit_action_and_practice", _("Can edit action_and_practice")),
            ("can_edit_link", _("Can edit link")),
            ("can_edit_measurement", _("Can edit measurement")),
            ("can_edit_object_name", _("Can edit object_name")),
            ("can_edit_category", _("Can edit category")),
            ("can_edit_context", _("Can edit context")),
            ("can_edit_scope", _("Can edit scope")),
            ("can_edit_seq", _("Can edit seq")),
            ("can_edit_source", _("Can edit source")),
            ("can_edit_start_date_year", _("Can edit start_date_year")),
            ("can_edit_end_date_year", _("Can edit end_date_year")),
            ("can_edit_validity", _("Can edit validity")),
            ("can_edit_code", _("Can edit code")),
            ("can_edit_thematic_areas", _("Can edit thematic_areas")),
            ("can_edit_locations", _("Can edit locations")),
            ("can_edit_raw_datas", _("Can edit raw_datas")),
            ("can_edit_summarized", _("Can edit summarized")),
            ("can_edit_link_to_data", _("Can edit link to data")),
            ("can_edit_link_to_graphic", _("Can edit link do graphic")),
        )
        indexes = [
            models.Index(fields=["action_and_practice"]),
            models.Index(fields=["code"]),
            models.Index(fields=["description"]),
            models.Index(fields=["end_date_year"]),
            models.Index(fields=["link"]),
            models.Index(fields=["measurement"]),
            models.Index(fields=["posterior_record"]),
            models.Index(fields=["previous_record"]),
            models.Index(fields=["record_status"]),
            models.Index(fields=["object_name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["context"]),
            models.Index(fields=["scope"]),
            models.Index(fields=["seq"]),
            models.Index(fields=["source"]),
            models.Index(fields=["start_date_year"]),
            models.Index(fields=["title"]),
            models.Index(fields=["validity"]),
        ]

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("keywords"),
        FieldPanel("code"),
        FieldPanel("link_to_graphic", permission="indicator.can_edit_link_to_graphic"),
        FieldPanel("link_to_data", permission="indicator.can_edit_link_to_data"),
        FieldPanel("record_status", permission="indicator.can_edit_record_status"),
        FieldPanel(
            "action_and_practice", permission="indicator.can_edit_action_and_practice"
        ),
        FieldPanel("link", permission="indicator.can_edit_link"),
        FieldPanel("measurement", permission="indicator.can_edit_measurement"),
        FieldPanel("object_name", permission="indicator.can_edit_object_name"),
        FieldPanel("category", permission="indicator.can_edit_category"),
        FieldPanel("context", permission="indicator.can_edit_context"),
        FieldPanel("scope", permission="indicator.can_edit_scope"),
        FieldPanel("seq", permission="indicator.can_edit_seq"),
        FieldPanel("source", permission="indicator.can_edit_source"),
        FieldPanel("start_date_year", permission="indicator.can_edit_start_date_year"),
        FieldPanel("end_date_year", permission="indicator.can_edit_end_date_year"),
        FieldPanel("validity", permission="indicator.can_edit_validity"),
        FieldPanel("code", permission="indicator.can_edit_code"),
        AutocompletePanel("thematic_areas", permission="indicator.can_edit_thematic_areas"),
        AutocompletePanel("locations", permission="indicator.can_edit_locations"),
        FieldPanel("raw_data", permission="indicator.can_edit_raw_datas"),
        FieldPanel("summarized", permission="indicator.can_edit_summarized"),
    ]

    # https://drive.google.com/drive/folders/1_J8iKhr_gayuBqtvnSWreC-eBnxzY9rh
    # IDENTIDADE sugerido:
    #      (seq + action + classification) +
    #      (created + creator_id) +
    #      (validity + previous + posterior) +
    #      (title)
    # ID melhorado:
    #    action + classification + practice + scope + seq
    def __unicode__(self):
        return f"{self.title} {self.seq} {self.validity} {self.updated}"

    def __str__(self):
        return f"{self.title} {self.seq} {self.validity} {self.updated}"

    @property
    def filename(self):
        items = [
            self.title,
            str(self.seq),
            self.updated.isoformat().replace(":", "")[:15],
        ]
        return slugify("_".join(items).lower())

    base_form_class = IndicatorDirectoryForm
