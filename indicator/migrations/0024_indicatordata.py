# Generated by Django 4.1.6 on 2024-08-08 10:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_language"),
        ("indicator", "0023_alter_indicatorfile_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="IndicatorData",
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
                ("name", models.CharField(max_length=255, verbose_name="Nome")),
                (
                    "data_type",
                    models.CharField(max_length=255, verbose_name="Data Type"),
                ),
                (
                    "raw",
                    models.JSONField(
                        blank=True, null=True, verbose_name="Arquivo JSON"
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Data de criação"
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Data da última atualização"
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="core.source",
                        verbose_name="Origem",
                    ),
                ),
            ],
        ),
    ]
