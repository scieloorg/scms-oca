# Generated manually for SciELO ArticleMeta harvest support.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ("harvest", "0003_alter_harvestedbooks_created_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HarvestedArticle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="Creation date"),
                ),
                (
                    "updated",
                    models.DateTimeField(auto_now=True, verbose_name="Last update date"),
                ),
                (
                    "identifier",
                    models.CharField(
                        db_index=True,
                        help_text="Identificador único do registro no sistema externo",
                        max_length=255,
                        unique=True,
                        verbose_name="ID Externo",
                    ),
                ),
                (
                    "source_url",
                    models.URLField(blank=True, null=True, verbose_name="URL da Fonte"),
                ),
                (
                    "raw_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Dados completos retornados pelo endpoint",
                        verbose_name="Dados Brutos",
                    ),
                ),
                (
                    "harvest_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("in_progress", "Em Progresso"),
                            ("success", "Sucesso"),
                            ("failed", "Falhou"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                        verbose_name="Status da Coleta",
                    ),
                ),
                (
                    "index_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("in_progress", "Em Progresso"),
                            ("success", "Sucesso"),
                            ("failed", "Falhou"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                        verbose_name="Status da Indexação",
                    ),
                ),
                (
                    "datestamp",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Data do registro",
                    ),
                ),
                (
                    "last_harvest_attempt",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Última Tentativa de Coleta",
                    ),
                ),
                (
                    "indexed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Indexado em",
                    ),
                ),
                (
                    "index_name",
                    models.CharField(
                        blank=True,
                        help_text="Nome do índice no OpenSearch onde foi indexado",
                        max_length=100,
                        null=True,
                        verbose_name="Nome do Índice",
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_creator",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creator",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_last_mod_user",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updater",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dados de artigo SciELO",
                "verbose_name_plural": "Dados de artigos SciELO",
            },
        ),
        migrations.CreateModel(
            name="HarvestErrorLogArticle",
            fields=[
                (
                    "baseharvesterrorlog_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="harvest.baseharvesterrorlog",
                    ),
                ),
                (
                    "article",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="harvest_error_log",
                        to="harvest.harvestedarticle",
                    ),
                ),
            ],
            bases=("harvest.baseharvesterrorlog",),
        ),
        migrations.AddIndex(
            model_name="harvestedarticle",
            index=models.Index(fields=["identifier"], name="harvest_har_identif_8c352b_idx"),
        ),
        migrations.AlterField(
            model_name="transformationscript",
            name="harvest_model",
            field=models.CharField(
                blank=True,
                choices=[
                    ("HarvestedArticle", "Article"),
                    ("HarvestedPreprint", "Preprint"),
                    ("HarvestedBooks", "Books"),
                    ("HarvestedSciELOData_dataset", "SciELO Data - Dataset"),
                    ("HarvestedSciELOData_dataverse", "SciELO Data - Dataverse"),
                ],
                db_index=True,
                help_text="Modelo de coleta associado a este script para transformação automática",
                max_length=50,
                null=True,
                verbose_name="Modelo de Coleta",
            ),
        ),
    ]
