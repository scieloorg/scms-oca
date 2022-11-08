import os
from zipfile import ZipFile
from datetime import datetime
import logging
import csv
import io
import json

from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.edit_handlers import FieldPanel

from core.models import CommonControlField

from scholarly_articles import choices as scholarly_articles_choices
from . import choices
from .forms import IndicatorDirectoryForm
from usefulmodels.models import Action, Practice, ThematicArea, ActionAndPractice
from institution.models import Institution
from location.models import Location
from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory


class ScientificProduction(models.Model):
    communication_object = models.CharField(
        _("Communication object"),
        max_length=25, null=True, blank=True)
    open_access_status = models.CharField(
        _("Open Access Status"), max_length=50,
        null=True, blank=True)
    use_license = models.CharField(
        _("Use License"), max_length=50,
        null=True, blank=True)
    apc = models.CharField(
        _("Article Processing Charge"), max_length=20,
        null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['communication_object']),
            models.Index(fields=['open_access_status']),
            models.Index(fields=['use_license']),
            models.Index(fields=['apc']),
        ]

    @classmethod
    def get_or_create(cls, communication_object, open_access_status, use_license, apc):
        try:
            return ScientificProduction.objects.get(
                communication_object=communication_object,
                open_access_status=open_access_status,
                use_license=use_license,
                apc=apc,
            )
        except ScientificProduction.DoesNotExist:
            return ScientificProduction(
                    communication_object=communication_object,
                    open_access_status=open_access_status,
                    use_license=use_license,
                    apc=apc,
                ).save()
        except ScientificProduction.MultipleObjectsReturned:
            return ScientificProduction.objects.filter(
                    communication_object=communication_object,
                    open_access_status=open_access_status,
                    use_license=use_license,
                    apc=apc,
                ).first()


class Indicator(CommonControlField):

    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    description = models.TextField(_("Description"), max_length=1000,
                                   null=True, blank=True)

    validity = models.CharField(_("Record validity"), choices=choices.VALIDITY,
                                     max_length=255, null=True, blank=True)
    previous_record = models.ForeignKey(
        'self',
        verbose_name=_("Previous Record"),
        related_name="predecessor_register",
        on_delete=models.SET_NULL,
        max_length=255, null=True, blank=True)
    posterior_record = models.ForeignKey(
        'self',
        verbose_name=_("Posterior Record"),
        related_name="successor_register",
        on_delete=models.SET_NULL,
        max_length=255, null=True, blank=True)
    seq = models.IntegerField(_('Sequential number'), null=True, blank=True)

    action_and_practice = models.ForeignKey(ActionAndPractice, on_delete=models.SET_NULL, null=True)
    thematic_areas = models.ManyToManyField(ThematicArea, verbose_name=_("Thematic Area"), blank=True)
    institutions = models.ManyToManyField(Institution, verbose_name=_("Institution"), blank=True)
    locations = models.ManyToManyField(Location, verbose_name=_("Location"),  blank=True)
    start_date_year = models.IntegerField(_("Start Date"), null=True, blank=True)
    end_date_year = models.IntegerField(_("End Date"), null=True, blank=True)

    link = models.URLField(_("Link"), null=True, blank=True)
    raw_data = models.FileField(_("JSONL Zip File"), null=True, blank=True, max_length=255)
    summarized = models.JSONField(_("JSON File"), null=True, blank=True)

    keywords = TaggableManager(_("Keywords"), blank=True)

    record_status = models.CharField(_("Record status"), choices=choices.status,
                                     max_length=255, null=True, blank=True)
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)

    scope = models.CharField(_('Scope'), choices=choices.SCOPE, max_length=20, null=True)
    measurement = models.CharField(_('Measurement'), choices=choices.MEASUREMENT_TYPE, max_length=25, null=True)
    code = models.CharField(_("Code"), max_length=555, null=False, blank=False)
    scientific_production = models.ForeignKey(
        'ScientificProduction', on_delete=models.SET_NULL,
        null=True, blank=False,
    )

    def save_raw_data(self, items):
        file_path = os.path.join(settings.MEDIA_ROOT, self.filename + ".zip")
        with ZipFile(file_path, "w") as zf:
            zf.writestr(
                self.filename + ".jsonl",
                "".join(self._raw_data_rows(items)))
        self.raw_data.name = file_path
        self.save()

    def _raw_data_rows(self, items):
        for item in items:
            try:
                data = item.data
            except:
                data = {"teste": "teste"}
            yield f"{json.dumps(data)}\n"

    class Meta:
        indexes = [
            models.Index(fields=['action_and_practice']),
            models.Index(fields=['code']),
            models.Index(fields=['description']),
            models.Index(fields=['end_date_year']),
            models.Index(fields=['link']),
            models.Index(fields=['measurement']),
            models.Index(fields=['posterior_record']),
            models.Index(fields=['previous_record']),
            models.Index(fields=['record_status']),
            models.Index(fields=['scientific_production']),
            models.Index(fields=['scope']),
            models.Index(fields=['seq']),
            models.Index(fields=['source']),
            models.Index(fields=['start_date_year']),
            models.Index(fields=['title']),
            models.Index(fields=['validity']),
        ]

    panels = [
        FieldPanel('title'),
        FieldPanel('description'),
        FieldPanel('keywords'),
        FieldPanel('record_status'),
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
        return f"{self.title} {self.seq} {self.validity} {self.created}"

    def __str__(self):
        return f"{self.title} {self.seq} {self.validity} {self.created}"

    @property
    def filename(self):
        name = "".join([c if c.isalnum() else '_' for c in self.title])
        items = name.lower().split() + [
            self.created.isoformat().replace(':', '')[:15], str(self.seq)]
        return "_".join([
            item or ''
            for item in items
        ])

    base_form_class = IndicatorDirectoryForm
