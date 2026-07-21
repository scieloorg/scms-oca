from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WorldRegionsUpload",
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
                    "file",
                    models.FileField(
                        upload_to="world_regions/", verbose_name="Arquivo"
                    ),
                ),
                ("mapping", models.JSONField(default=dict, editable=False)),
                (
                    "active",
                    models.BooleanField(
                        db_index=True, default=False, verbose_name="Ativo"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("applying", "Aplicando"),
                            ("applied", "Aplicado"),
                            ("failed", "Falhou"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
                (
                    "task_id",
                    models.CharField(blank=True, max_length=255, verbose_name="Tarefa"),
                ),
                (
                    "current_task_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Tarefa atual do OpenSearch",
                    ),
                ),
                (
                    "current_index",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Índice atual"
                    ),
                ),
                ("stats", models.JSONField(blank=True, default=dict, editable=False)),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Iniciado em"
                    ),
                ),
                (
                    "finished_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Finalizado em"
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="Criado em"),
                ),
                (
                    "updated",
                    models.DateTimeField(auto_now=True, verbose_name="Atualizado em"),
                ),
            ],
            options={
                "verbose_name": "Tabela de regiões mundiais",
                "verbose_name_plural": "Tabelas de regiões mundiais",
                "ordering": ("-created",),
            },
        ),
    ]
