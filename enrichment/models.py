from pathlib import Path

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel

from enrichment.parsing import parse_world_regions


class BaseEnrichmentUpload(CommonControlField):
    target_data_source = models.ForeignKey(
        "search_gateway.DataSource",
        verbose_name=_("Índices de destino"),
        help_text=_("Selecione os índices onde os dados serão aplicados"),
        on_delete=models.PROTECT,
    )
    file = models.FileField(
        _("Arquivo"),
        upload_to="enrichment/",
    )

    panels = [
        FieldPanel("target_data_source"),
        FieldPanel("file"),
    ]

    class Meta:
        abstract = True

    def __str__(self):
        return Path(self.file.name).name if self.file else str(self.pk)

    @property
    def target_index_name(self):
        return self.target_data_source.index_name


class WorldRegionsUpload(BaseEnrichmentUpload):
    base_form_class = WorldRegionsUploadForm

    class WorldRegionsStatus(models.TextChoices):
        PENDING = "pending", _("Pendente")
        APPLYING = "applying", _("Aplicando")
        APPLIED = "applied", _("Aplicado")
        FAILED = "failed", _("Falhou")

    mapping = models.JSONField(default=dict, editable=False)
    active = models.BooleanField(_("Ativo"), default=False, db_index=True)
    status = models.CharField(
        _("Status"),
        max_length=16,
        choices=WorldRegionsStatus,
        default=WorldRegionsStatus.PENDING,
        db_index=True,
    )
    stats = models.JSONField(default=dict, blank=True, editable=False)
    started_at = models.DateTimeField(_("Iniciado em"), null=True, blank=True)
    finished_at = models.DateTimeField(_("Finalizado em"), null=True, blank=True)

    class Meta:
        verbose_name = _("Tabela de regiões mundiais")
        verbose_name_plural = _("Tabelas de regiões mundiais")
        ordering = ("-created",)

    def clean(self):
        super().clean()

        if not self.file:
            return

        if Path(self.file.name).suffix.lower() != ".csv":
            raise ValidationError({"file": _("Envie um arquivo CSV.")})

        self.mapping = parse_world_regions(self.file)
