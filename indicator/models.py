import json
import logging
import os
import secrets
from datetime import datetime
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.dispatch.dispatcher import receiver
from django.utils.text import slugify
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.utils import utils
from core.models import CommonControlField
from institution.models import Institution
from location.models import Location
from usefulmodels.models import ActionAndPractice, ThematicArea

from . import choices
from .forms import IndicatorDirectoryForm
from .permission_helper import MUST_BE_MODERATE


class GetOrCreateCrontabScheduleError(Exception): ...


class CreateIndicatorRecordError(Exception): ...


class IndicatorFile(models.Model):
    """
    This class store a file .zip with the raw data to indicator.
    """

    name = models.CharField(_("File name"), max_length=1024, null=False, blank=False)
    raw_data = models.FileField(_("JSONL Zip File"), null=True, blank=True)
    is_dynamic_data = models.BooleanField(
        _("Dynamic Data"), default=False, null=True, blank=True
    )
    autocomplete_search_field = "name"

    def extension(self):
        name, extension = os.path.splitext(self.raw_data.name)
        return extension

    class Meta:
        ordering = ("id",)

    def autocomplete_label(self):
        return str(self)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__()


@receiver(models.signals.post_delete, sender=IndicatorFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `IndicatorFile` object is deleted.
    """
    if instance.raw_data:
        if os.path.isfile(instance.raw_data.path):
            os.remove(instance.raw_data.path)


@receiver(models.signals.pre_save, sender=IndicatorFile)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem
    when corresponding `IndicatorFile` object is updated
    with new file.
    """
    if not instance.pk:
        return False

    try:
        old_file = IndicatorFile.objects.get(pk=instance.pk).raw_data
    except IndicatorFile.DoesNotExist:
        return False

    new_file = instance.raw_data
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)


@receiver(models.signals.post_delete, sender=IndicatorFile)
def delete_file(sender, instance, *args, **kwargs):
    """Deletes image files on `post_delete`"""
    if instance.raw_data:
        utils.delete_file(instance.raw_data.path)


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

    indicator_file = models.ManyToManyField(
        IndicatorFile, verbose_name=_("Indicator File"), blank=True
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

    institutional_contribution = models.CharField(
        _("Institutional Contribution"),
        max_length=255,
        default=settings.DIRECTORY_DEFAULT_CONTRIBUTOR,
        help_text=_("Name of the contributing institution, default=SciELO."),
    )

    notes = models.TextField(_("Notes"), max_length=1000, null=True, blank=True)

    # @classmethod
    # def delete(cls):
    #     for item in cls.objects.iterator():
    #         try:
    #             item.action_and_practice = None
    #             if item.thematic_areas:
    #                 item.thematic_areas.clear()
    #             if item.institutions:
    #                 item.institutions.clear()
    #             if item.locations:
    #                 item.locations.clear()
    #         except Exception as e:
    #             logging.exception(e)
    #     cls.objects.all().delete()

    def save(self, *args, **kwargs):
        # ensure we always have the slug.
        if not self.slug:
            self.slug = secrets.token_urlsafe(48)
        return super().save(*args, **kwargs)

    def get_absolute_edit_url(self):
        return f"/indicator/indicator/edit/{self.id}/"

    @property
    def permanent_link(self):
        return "https://ocabr.org/search/indicator/{}/detail/".format(self.slug)

    @property
    def header(self):
        link = self.permanent_link
        practice = None
        action = None
        classification = None
        if self.action_and_practice:
            if self.action_and_practice.action:
                action = self.action_and_practice.action.name
            if self.action_and_practice.practice:
                practice = self.action_and_practice.practice.name
            classification = self.action_and_practice.classification
        d = dict(
            title=self.title,
            description=self.description,
            validity=self.validity,
            version=self.seq,
            link=link,
            source="OCABr",
            updated=self.updated.isoformat(),
            contributors=["SciELO"],
            action=action,
            practice=practice,
            qualification=classification,
            license="CC-BY",
        )
        indicator = {}
        indicator["indicator"] = {k: v for k, v in d.items() if v}
        return indicator

    def save_raw_data(self, items, ids):
        """
        This function generate the .zip file to a list of items and relate this .zip
        with the indicator.
        """
        if items:
            with TemporaryDirectory() as tmpdirname:
                temp_zip_file_path = os.path.join(tmpdirname, self.filename + ".zip")
                logging.info("temp file_path %s" % temp_zip_file_path)

                with ZipFile(temp_zip_file_path, "w") as zf:
                    zf.writestr(
                        self.filename + ".jsonl", "".join(self._raw_data_rows(items))
                    )
                zf.close()

                zfile = open(temp_zip_file_path, "rb")

                ind_file = IndicatorFile(name=self.filename)
                ind_file.raw_data.save(self.filename + ".zip", zfile)
                ind_file.data_ids = ids
                ind_file.save()

            logging.info(
                "existe file_path? %s" % os.path.isfile(ind_file.raw_data.path)
            )

            self.indicator_file = ind_file
            self.save()

    def _raw_data_rows(self, items):
        for item in items:
            try:
                data = item.data
            except Exception as e:
                logging.exception(e)
            else:
                data.update(self.header)
                try:
                    yield f"{json.dumps(data)}\n"
                except Exception as e:
                    logging.exception(e)
                    logging.exception(data)

    @property
    def disclaimer(self):
        if self.institutional_contribution != settings.DIRECTORY_DEFAULT_CONTRIBUTOR:
            if self.updated_by:
                return (
                    _("Conteúdo publicado sem moderação / contribuição de %s")
                    % self.institutional_contribution
                    if not self.updated_by.is_staff
                    and self.record_status == "PUBLISHED"
                    else None
                )

            if self.creator:
                return (
                    _("Conteúdo publicado sem moderação / contribuição de %s")
                    % self.institutional_contribution
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
            ("can_edit_notes", _("Can edit notes")),
        )
        indexes = [
            models.Index(fields=["action_and_practice"]),
            models.Index(fields=["code"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["end_date_year"]),
            models.Index(fields=["link"]),
            models.Index(fields=["measurement"]),
            models.Index(fields=["posterior_record"]),
            models.Index(fields=["previous_record"]),
            models.Index(fields=["record_status"]),
            models.Index(fields=["object_name"]),
            models.Index(fields=["category"]),
            # models.Index(fields=["context"]),
            # models.Index(fields=["scope"]),
            # models.Index(fields=["seq"]),
            models.Index(fields=["source"]),
            models.Index(fields=["start_date_year"]),
            models.Index(fields=["title"]),
            models.Index(fields=["validity"]),
        ]

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("institutional_contribution"),
        FieldPanel("keywords"),
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
        AutocompletePanel(
            "thematic_areas", permission="indicator.can_edit_thematic_areas"
        ),
        AutocompletePanel("locations", permission="indicator.can_edit_locations"),
        FieldPanel("summarized", permission="indicator.can_edit_summarized"),
        FieldPanel("notes", permission="indicator.can_edit_notes"),
        AutocompletePanel("indicator_file"),
    ]

    def __unicode__(self):
        return f"{self.title} {self.seq} {self.validity} {self.updated}"

    def __str__(self):
        return f"{self.title} {self.seq} {self.validity} {self.updated}"

    @property
    def filename(self):
        items = [
            self.title,
            self.updated.isoformat().replace(":", "")[:15],
        ]
        return slugify("_".join(items).lower())

    base_form_class = IndicatorDirectoryForm

    @classmethod
    def get(cls, key, **kwargs):
        """
        Retorna Indicador com qualquer chave.
        Sugiro testar indicator.id == key e fazer redirect.

        Raises
        ------
        cls.DoesNotExist
        """
        try:
            return cls.objects.get(Q(slug=key) | Q(code=key), **kwargs)
        except cls.DoesNotExist:
            try:
                return cls.objects.get(id=int(key), **kwargs)
            except (TypeError, ValueError):
                raise cls.DoesNotExist(key)

    @property
    def name(self):
        """
        Gera parte do título: "Número de XXXx"
        """
        # Número de | Evolução do número de | Porcentagem de
        d = dict(choices.MEASUREMENT_TYPE)
        d["FREQUENCY"] = _("Número")
        d["EVOLUTION"] = _("Evolução do número")

        measurement_title = d.get(self.measurement) + " " + _("de")
        return f"{measurement_title} {self.object_name}"

    @classmethod
    def build_old_code(
        cls,
        action,
        classification,
        practice,
        measurement,
        object_name,
        start_date_year,
        end_date_year,
        category1_id,
        category2_id,
        context,
    ):
        items = [
            action and action.code or "",
            slugify(classification) or "",
            practice and practice.code or "",
            measurement,
            object_name,
            category2_id or category1_id or "",
            start_date_year or "",
            end_date_year or "",
        ] + (context or [])
        return _str_with_64_char(slugify("_".join(items)).upper())

    @classmethod
    def get_latest_version_by_code(cls, code):
        """
        Obtém a versão mais recente de uma instância de Indicator,

        Parameters
        ----------
        code : str
        """
        try:
            return cls.objects.filter(code=code).latest("created")
        except cls.DoesNotExist as e:
            return None

    @property
    def latest(self):
        """
        Obtém a versão mais recente de uma instância de Indicator,

        """
        curr = self
        while True:
            if not curr.posterior_record:
                return curr
            curr = curr.posterior_record

    @classmethod
    def get_latest_version(
        cls,
        source,
        object_name,
        measurement,
        category=None,
        context=None,
        start_date_year=None,
        end_date_year=None,
        action=None,
        classification=None,
        practice=None,
    ):
        action_and_practice = None
        if action or classification or practice:
            action_and_practice = ActionAndPractice.get_or_create(
                action, classification, practice
            )
        try:
            return cls.objects.filter(
                source=source,
                object_name=object_name,
                measurement=measurement,
                category=category,
                context=context,
                start_date_year=start_date_year,
                end_date_year=end_date_year,
                action_and_practice=action_and_practice,
                posterior_record__isnull=True,
            ).latest("created")
        except cls.DoesNotExist as e:
            return None

    @classmethod
    def get_latest_version_by_slug(cls, slug):
        """
        Obtém a versão mais recente de uma instância de Indicator,

        Parameters
        ----------
        slug : str
        """
        try:
            return cls.objects.get(slug=slug, posterior_record__isnull=True)
        except cls.DoesNotExist as exc:
            try:
                curr = cls.objects.get(slug=slug)
            except cls.DoesNotExist as exc:
                return None
            else:
                while True:
                    next_ = curr.posterior_record
                    if not next_:
                        return curr
                    curr = next_

    def generate_title(self):
        name = self.name

        # por área temática | por instit | por UF
        by_category = ""
        if self.category:
            by_category = " " + _("por") + " " + _(self.category)

        # ano ou intervalo de anos
        years = ""
        if self.start_date_year:
            years = f" - {self.start_date_year}"
            if self.end_date_year and self.start_date_year != self.end_date_year:
                years += f"-{self.end_date_year}"

        # contexto institucional, geográfico, temático
        # Universidade X | SP | Ciências Biológicas
        context = self.context and f" - {self.context}" or ""

        return f"{name}{by_category}{years}{context}"

    @property
    def object_code(self):
        """
        Retorna código do objeto para o qual o indicador está sendo gerado
        """
        try:
            return (
                self.action_and_practice.classification
                or self.action_and_practice.action.code
            )
        except AttributeError:
            return ""

    def set_code(self):
        """
        Sugestão
        https://docs.google.com/document/d/1nOvMLwsePKA5BHOYQiwGOrQDskFsxM4M/edit
        ----------------------------------------------
        Identidade = {(ação, versão, postagem, nome)}
        versão = id, status
        status = ativo | inativo
        inativo = anterior, posterior
        postagem = {(data, autoria)}
        nome = Número de documentos ...
        ----------------------------------------------
        Mas:

        object_code - ex.: políticas | journal-article | ações | ...
        tipo de indicador - ex.: freq | evol | perc | ...
        categoria - ex.: por área temática, por instituição, por UF,
        data início, data fim - data dos dados
        contexto - UF | Instituição | Área temática
        fonte - criador do indicador
        data de criação do indicador
        """
        # ação ou objeto (ex.: políticas, journal-article, ações, ...)
        items = (
            self.object_code,
            self.measurement[:4],
            self.category or "",
            self.context or "",
            self.start_date_year or "",
            self.end_date_year or "",
            self.source or "",
            self.created.isoformat()[:10],
        )
        self.code = slugify("-".join(items)).lower()[:500]

    @classmethod
    def create(
        cls,
        creator,
        source,
        object_name,
        measurement,
        category=None,
        context=None,
        start_date_year=None,
        end_date_year=None,
        title=None,
        action=None,
        classification=None,
        practice=None,
        keywords=None,
        institutions=None,
        locations=None,
        thematic_areas=None,
        # institutional_contribution=None,
    ):
        latest = cls.get_latest_version(
            source,
            object_name,
            measurement,
            category=category,
            context=context,
            start_date_year=start_date_year,
            end_date_year=end_date_year,
            action=action,
            classification=classification,
            practice=practice,
        )
        if latest and latest.record_status == choices.WIP:
            raise CreateIndicatorRecordError(
                "Indicator is being generated {} {} {}".format(
                    latest.code, latest.seq, latest.created
                )
            )
        new = latest and latest.create_new_from_latest(creator)
        if not new:
            new = cls()
            if action or classification or practice:
                new.action_and_practice = ActionAndPractice.get_or_create(
                    action, classification, practice
                )
            new.measurement = measurement
            new.object_name = object_name
            new.source = source
            new.category = category
            new.context = context
            new.start_date_year = start_date_year
            new.end_date_year = end_date_year

            # new.institutional_contribution = institutional_contribution
            new.title = title or new.generate_title()

            new.seq = 1

            new.creator = creator
            new.created = datetime.utcnow()
            new.save()
            new.set_code()

            logging.info(type((thematic_areas)))
            if thematic_areas is not None:
                new.thematic_areas.set(thematic_areas)
            if institutions is not None:
                new.institutions.set(institutions)
            if locations is not None:
                new.locations.set(locations)
            if keywords:
                new.keywords.add(*keywords)

            if institutions:
                scope = choices.INSTITUTIONAL
            elif thematic_areas:
                scope = choices.THEMATIC
            elif locations:
                scope = choices.GEOGRAPHIC
            else:
                scope = choices.GENERAL
            new.scope = scope

        new.record_status = choices.WIP
        new.previous_record = latest
        new.save()

        return new

    def create_new_from_latest(self, creator):
        if not self.posterior_record:
            return

        new = Indicator()
        new.measurement = self.measurement
        new.object_name = self.object_name
        new.source = self.source
        new.category = self.category
        new.context = self.context
        new.start_date_year = self.start_date_year
        new.end_date_year = self.end_date_year

        new.description = self.description

        new.scope = self.scope
        new.action_and_practice = self.action_and_practice

        new.previous_record = self

        new.title = self.title
        new.seq = self.seq + 1

        new.raw_data = None
        new.summarized = None

        new.institutional_contribution = None
        new.link_to_graphic = None
        new.link_to_data = None
        new.link = None

        new.slug = None
        new.record_status = None
        new.validity = None
        new.posterior_record = None

        new.creator = creator
        new.created = datetime.utcnow()

        new.save()

        new.set_code()
        new.thematic_areas.set(self.thematic_areas)
        new.institutions.set(self.institutions)
        new.locations.set(self.locations)
        new.keywords.set(self.keywords)
        new.save()

        return new

    def add_contribution(
        self,
        institutional_contribution=None,
        link_to_graphic=None,
        link_to_data=None,
        link=None,
    ):
        self.institutional_contribution = institutional_contribution
        self.link_to_graphic = link_to_graphic
        self.link_to_data = link_to_data
        self.link = link

    def add_raw_data(self, items):
        logging.info(
            f"Saving raw data {self.code} {self.object_name} {self.category} {self.context}"
        )
        self.save_raw_data(items)
        logging.info(
            f"Saved raw data {self.code} {self.object_name} {self.category} {self.context}"
        )
        self.record_status = choices.PUBLISHED
        self.validity = choices.CURRENT
        self.save()

        if self.previous_record:
            self.previous_record.posterior_record = self
            self.previous_record.validity = choices.OUTDATED
            self.previous_record.save()

    def add_context(self, institutions=None, locations=None, thematic_areas=None):
        if institutions or locations or thematic_areas:
            self.save()
            self.institutions.set(institutions)
            self.locations.set(locations)
            self.thematic_areas.set(thematic_areas)
            self.save()
