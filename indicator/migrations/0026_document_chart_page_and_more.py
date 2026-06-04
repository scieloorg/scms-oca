import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indicator", "0025_indicatorfile_description_indicatorfile_label"),
        ("search_gateway", "0005_datasource_metric_config"),
        ("wagtailcore", "0096_referenceindex_referenceindex_source_object_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentChartPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "intro",
                    wagtail.fields.RichTextField(
                        blank=True,
                        help_text="Introductory text displayed above the charts.",
                    ),
                ),
                (
                    "study_unit",
                    models.CharField(
                        choices=[
                            ("document", "Document"),
                            ("source", "Source"),
                        ],
                        default="document",
                        help_text="Study unit for data aggregation.",
                        max_length=50,
                        verbose_name="Study Unit",
                    ),
                ),
                (
                    "data_source",
                    models.ForeignKey(
                        blank=True,
                        help_text="OpenSearch data source linked to this chart.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="search_gateway.datasource",
                    ),
                ),
            ],
            options={
                "verbose_name": "Document Chart Page",
                "verbose_name_plural": "Document Chart Pages",
            },
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="SourceChartPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "intro",
                    wagtail.fields.RichTextField(
                        blank=True,
                        help_text="Introductory text displayed above the charts.",
                    ),
                ),
                (
                    "study_unit",
                    models.CharField(
                        choices=[
                            ("document", "Document"),
                            ("source", "Source"),
                        ],
                        default="document",
                        help_text="Study unit for data aggregation.",
                        max_length=50,
                        verbose_name="Study Unit",
                    ),
                ),
                (
                    "data_source",
                    models.ForeignKey(
                        blank=True,
                        help_text="OpenSearch data source linked to this chart.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="search_gateway.datasource",
                    ),
                ),
            ],
            options={
                "verbose_name": "Source Chart Page",
                "verbose_name_plural": "Source Chart Pages",
            },
            bases=("wagtailcore.page",),
        ),
    ]
