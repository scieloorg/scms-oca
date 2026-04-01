import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("observation", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ObservationDimension",
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
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                ("slug", models.SlugField(help_text="Unique identifier for this dimension in this page.", max_length=80, verbose_name="Slug")),
                ("menu_label", models.CharField(help_text="Label shown in the dimension selector above the table.", max_length=255, verbose_name="Menu label")),
                (
                    "row_field_name",
                    models.CharField(
                        help_text="DataSource field key used as row dimension (e.g. country, institution).",
                        max_length=100,
                        verbose_name="Row field name",
                    ),
                ),
                (
                    "col_field_name",
                    models.CharField(
                        default="publication_year",
                        help_text="DataSource field key used as column dimension.",
                        max_length=100,
                        verbose_name="Column field name",
                    ),
                ),
                ("row_bucket_size", models.PositiveIntegerField(default=500, verbose_name="Row bucket size")),
                ("col_bucket_size", models.PositiveIntegerField(default=300, verbose_name="Column bucket size")),
                ("table_title", models.CharField(max_length=255, verbose_name="Table title")),
                ("kpi_label", models.CharField(default="Documents", max_length=100, verbose_name="KPI label")),
                ("row_label", models.CharField(default="Country", max_length=100, verbose_name="Row label")),
                ("col_label", models.CharField(default="Year", max_length=100, verbose_name="Column label")),
                ("value_label", models.CharField(default="Documents", max_length=100, verbose_name="Value label")),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="If checked, this dimension is selected when the page loads.",
                        verbose_name="Default dimension",
                    ),
                ),
                (
                    "page",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dimensions",
                        to="observation.observationpage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Observation dimension",
                "verbose_name_plural": "Observation dimensions",
                "ordering": ["sort_order"],
            },
        ),
        migrations.AddConstraint(
            model_name="observationdimension",
            constraint=models.UniqueConstraint(
                fields=("page", "slug"),
                name="observation_dimension_unique_slug_per_page",
            ),
        ),
    ]
