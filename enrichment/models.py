from pathlib import Path

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel

from enrichment.parsing import parse_world_regions


class WorldRegionsStatus(models.TextChoices):
    PENDING = "pending", _("Pendente")
    APPLYING = "applying", _("Aplicando")
    APPLIED = "applied", _("Aplicado")
    FAILED = "failed", _("Falhou")


class WorldRegionsUpload(models.Model):
    file = models.FileField(_("Arquivo"), upload_to="world_regions/")
    mapping = models.JSONField(default=dict, editable=False)
    active = models.BooleanField(_("Ativo"), default=False, db_index=True)
    status = models.CharField(
        _("Status"),
        max_length=16,
        choices=WorldRegionsStatus.choices,
        default=WorldRegionsStatus.PENDING,
        db_index=True,
    )
    task_id = models.CharField(_("Tarefa"), max_length=255, blank=True)
    current_task_id = models.CharField(
        _("Tarefa atual do OpenSearch"),
        max_length=255,
        blank=True,
    )
    current_index = models.CharField(
        _("Índice atual"),
        max_length=255,
        blank=True,
    )
    stats = models.JSONField(default=dict, blank=True, editable=False)
    started_at = models.DateTimeField(_("Iniciado em"), null=True, blank=True)
    finished_at = models.DateTimeField(_("Finalizado em"), null=True, blank=True)
    created = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated = models.DateTimeField(_("Atualizado em"), auto_now=True)

    panels = [FieldPanel("file")]

    class Meta:
        verbose_name = _("Tabela de regiões mundiais")
        verbose_name_plural = _("Tabelas de regiões mundiais")
        ordering = ("-created",)

    def __str__(self):
        return Path(self.file.name).name if self.file else str(self.pk)

    def clean(self):
        super().clean()
        if not self.file:
            return

        if Path(self.file.name).suffix.lower() != ".csv":
            raise ValidationError({"file": _("Envie um arquivo CSV.")})

        self.mapping = parse_world_regions(self.file)

    @admin.display(description=_("Índices"))
    def completed_indices(self):
        return len(self.stats.get("indices", []))

    @admin.display(description=_("Encontrados"))
    def documents_found(self):
        return self.stats.get("total", 0)

    @admin.display(description=_("Atualizados"))
    def documents_updated(self):
        return self.stats.get("updated", 0)

    @admin.display(description=_("No-op"))
    def documents_noop(self):
        return self.stats.get("noops", 0)

    @admin.display(description=_("Falhas"))
    def failures(self):
        return self.stats.get("failures", 0)
