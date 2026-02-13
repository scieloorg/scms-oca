"""
Modelos para coleta e armazenamento de dados de múltiplos endpoints.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import ParentalKey

from core.forms import CoreAdminModelForm
from core.models import CommonControlField


class HarvestStatus(models.TextChoices):
    """Status de coleta de dados"""

    PENDING = "pending", _("Pendente")
    IN_PROGRESS = "in_progress", _("Em Progresso")
    SUCCESS = "success", _("Sucesso")
    FAILED = "failed", _("Falhou")


class IndexStatus(models.TextChoices):
    """Status de indexação"""

    PENDING = "pending", _("Pendente")
    IN_PROGRESS = "in_progress", _("Em Progresso")
    SUCCESS = "success", _("Sucesso")
    FAILED = "failed", _("Falhou")


class HarvestModelChoice(models.TextChoices):
    """Tipos de modelo de coleta para associar scripts de transformação"""

    PREPRINT = "HarvestedPreprint", "Preprint"
    BOOKS = "HarvestedBooks", "Books"
    SCIELO_DATA_DATASET = "HarvestedSciELOData_dataset", "SciELO Data - Dataset"
    SCIELO_DATA_DATAVERSE = "HarvestedSciELOData_dataverse", "SciELO Data - Dataverse"


class BaseHarvestedData(CommonControlField):
    """
    Modelo base abstrato para armazenar dados coletados de diferentes endpoints.
    Contém campos comuns a todos os tipos de dados.
    """

    identifier = models.CharField(
        _("ID Externo"),
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("Identificador único do registro no sistema externo"),
    )
    source_url = models.URLField(
        _("URL da Fonte"),
        blank=True,
        null=True,
    )
    raw_data = models.JSONField(
        _("Dados Brutos"),
        default=dict,
        blank=True,
        help_text=_("Dados completos retornados pelo endpoint"),
    )
    harvest_status = models.CharField(
        _("Status da Coleta"),
        max_length=20,
        choices=HarvestStatus.choices,
        default=HarvestStatus.PENDING,
        db_index=True,
    )
    index_status = models.CharField(
        _("Status da Indexação"),
        max_length=20,
        choices=IndexStatus.choices,
        default=IndexStatus.PENDING,
        db_index=True,
    )
    datestamp = models.DateTimeField(
        verbose_name=_("Data do registro"),
        blank=True,
        null=True,
    )
    last_harvest_attempt = models.DateTimeField(
        _("Última Tentativa de Coleta"), blank=True, null=True
    )
    indexed_at = models.DateTimeField(_("Indexado em"), blank=True, null=True)
    index_name = models.CharField(
        _("Nome do Índice"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Nome do índice no OpenSearch onde foi indexado"),
    )

    panels = [
        FieldPanel("identifier"),
        FieldPanel("source_url"),
        FieldPanel("raw_data"),
        FieldPanel("harvest_status"),
        FieldPanel("index_status"),
        FieldPanel("last_harvest_attempt"),
        FieldPanel("indexed_at"),
        FieldPanel("index_name"),
        InlinePanel("harvest_error_log"),
    ]

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["identifier"]),
        ]

    def __str__(self):
        return f"{self.identifier}"

    def mark_as_in_progress(self):
        self.harvest_status = HarvestStatus.IN_PROGRESS
        self.updated = timezone.now()
        self.save(update_fields=["harvest_status", "updated"])

    def mark_as_success(self):
        self.harvest_status = HarvestStatus.SUCCESS
        self.last_harvest_attempt = timezone.now()
        self.updated = timezone.now()
        self.save(update_fields=["harvest_status", "last_harvest_attempt", "updated"])

    def mark_as_failed(self, error_message=None):
        self.harvest_status = HarvestStatus.FAILED
        self.last_harvest_attempt = timezone.now()
        self.updated = timezone.now()
        self.save(update_fields=["harvest_status", "last_harvest_attempt", "updated"])

    def mark_as_indexed(self, index_name):
        self.index_status = IndexStatus.SUCCESS
        self.indexed_at = timezone.now()
        self.index_name = index_name
        self.updated = timezone.now()
        self.save(
            update_fields=[
                "harvest_status",
                "index_status",
                "indexed_at",
                "index_name",
                "updated",
            ]
        )

    def mark_as_index_failed(self, error_message=None):
        self.index_status = IndexStatus.FAILED
        self.updated = timezone.now()
        self.save(update_fields=["harvest_status", "index_status", "updated"])

    def set_attrs_from_article_info(self, article_info, datestamp):
        datestamp = datestamp if datestamp else None
        self.source_url = (
            article_info.get("source")[0] if article_info.get("source") else None
        )
        self.raw_data = article_info
        self.datestamp = datestamp
        self.last_harvest_attempt = datestamp
        self.save()

    def get_document_for_indexing(self):
        return self.raw_data


class HarvestedPreprint(BaseHarvestedData, ClusterableModel):
    """
    Modelo para dados de preprint.
    """

    class Meta:
        verbose_name = _("Dados de preprint puro")
        verbose_name_plural = _("Dados de preprint")


    @classmethod
    def get_latest_preprint(cls):
        # Recupera o ultimo registro de Preprint a partir do header.datestamp armazenado no campo datestamp
        try:
            return HarvestedPreprint.objects.latest("datestamp")
        except HarvestedPreprint.DoesNotExist:
            return None

    @classmethod
    def get_latest_preprint_token(cls):
        latest = (
            HarvestedPreprint.objects.exclude(last_resumption_token__isnull=True)
            .exclude(last_resumption_token="")
            .order_by("-updated")
            .first()
        )
        return latest.last_resumption_token if latest else None

class HarvestedBooks(BaseHarvestedData, ClusterableModel):
    type_data = models.CharField(
        _("Tipo de data"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Part ou Monograph"),
    )
    parent = models.ForeignKey(
        "self",
        verbose_name=_("Monograph"),
        related_name="parts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_("Monograph relacionado quando o tipo for Part"),
    )
    last_seq = models.BigIntegerField(
        _("Última sequência"),
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Sequência do _changes processada para este registro"),
    )

    panels = BaseHarvestedData.panels + [
        FieldPanel("type_data"),
        FieldPanel("parent"),
        FieldPanel("last_seq"),
    ]

    class Meta:
        verbose_name = _("Dados de Scielo Books")
        verbose_name_plural = _("Dados de Scielo Books")


class HarvestedSciELOData(BaseHarvestedData, ClusterableModel):
    type_data = models.CharField(
        _("Tipo de dado"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("dataset ou dataverse"),
    )

    class Meta:
        verbose_name = _("Dados de Scielo Data")
        verbose_name_plural = _("Dados de Scielo")

    @property
    def get_url_dataverse(self):
        return self.raw_data.get("theme", {}).get("linkUrl")

class BaseHarvestErrorLog(models.Model):
    field_name = models.CharField(
        _("Campo com Erro"),
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Nome do campo que causou o erro, se aplicável"),
    )
    exception_type = models.TextField(_("Exception Type"), null=True, blank=True)
    exception_message = models.TextField(
        _("Mensagem de Erro"), help_text=_("Descrição detalhada do erro")
    )

    exception_traceback = models.TextField(
        _("Traceback do Erro"),
        blank=True,
        null=True,
        help_text=_("Stack trace completo do erro (para debugging)"),
    )
    is_resolved = models.BooleanField(
        _("Erro Resolvido"),
        default=False,
        db_index=True,
        help_text=_("Indica se o erro foi resolvido"),
    )
    occurrence_date = models.DateTimeField(
        _("Data de ocorrência"),
        blank=True,
        null=True,
    )
    context_data = models.JSONField(
        _("Dados de Contexto"),
        default=dict,
        blank=True,
        help_text=_("Informações adicionais sobre o contexto do erro"),
    )
    resolved_at = models.DateTimeField(
        _("Resolvido em"),
        blank=True,
        null=True,
        help_text=_("Quando o erro foi resolvido"),
    )


class HarvestErrorLogPreprint(BaseHarvestErrorLog):
    preprint = ParentalKey(
        HarvestedPreprint, related_name="harvest_error_log", on_delete=models.CASCADE
    )


class HarvestErrorLogBooks(BaseHarvestErrorLog):
    book = ParentalKey(
        HarvestedBooks, related_name="harvest_error_log", on_delete=models.CASCADE
    )


class HarvestErrorLogSciELOData(BaseHarvestErrorLog):
    scielo_data = ParentalKey(
        HarvestedSciELOData, related_name="harvest_error_log", on_delete=models.CASCADE
    )

class TransformationScript(CommonControlField):
    """
    Modelo para armazenar scripts Painless de transformação de dados.
    Permite configurar via interface a transformação de dados raw para bronze.
    """

    name = models.CharField(
        _("Nome"),
        max_length=100,
        help_text=_("Nome identificador do script de transformação"),
    )
    description = models.TextField(
        _("Descrição"),
        blank=True,
        null=True,
        help_text=_("Descrição do que este script faz"),
    )
    source_index = models.CharField(
        _("Índice de Origem"),
        max_length=100,
        help_text=_("Nome do índice OpenSearch de origem (ex: raw_scielo_book)"),
    )
    dest_index = models.CharField(
        _("Índice de Destino"),
        max_length=100,
        help_text=_("Nome do índice OpenSearch de destino (ex: bronze_scielo_books)"),
    )
    query_script = models.TextField(
        _("Query JSON"),
        help_text=_(
            "Query JSON para selecionar documentos. "
            "Use {{identifier}} como placeholder para o ID do documento."
        ),
        null=True,
        blank=True
    )
    transform_script = models.TextField(
        _("Script Painless"),
        help_text=_(
            "Script Painless para transformação dos dados. "
            "Acesse os dados brutos via ctx._source.raw_data"
        ),
    )
    is_active = models.BooleanField(
        _("Ativo"),
        default=True,
        db_index=True,
        help_text=_("Se desativado, a transformação não será executada"),
    )
    harvest_model = models.CharField(
        _("Modelo de Coleta"),
        max_length=50,
        choices=HarvestModelChoice.choices,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Modelo de coleta associado a este script para transformação automática"),
    )

    panels = [
        FieldPanel("harvest_model"),
        FieldPanel("name"),
        FieldPanel("description"),
        FieldPanel("source_index"),
        FieldPanel("dest_index"),
        FieldPanel("is_active"),
        FieldPanel("query_script"),
        FieldPanel("transform_script"),
    ]

    class Meta:
        verbose_name = _("Script de Transformação")
        verbose_name_plural = _("Scripts de Transformação")

    def __str__(self):
        return f"{self.name} ({self.source_index})"
    
    base_form_class = CoreAdminModelForm
