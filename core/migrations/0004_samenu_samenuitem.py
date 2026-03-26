import django.db.models.deletion
import modelcluster.fields
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_alter_language_options_alter_language_code2_and_more"),
        ("wagtailcore", "0096_referenceindex_referenceindex_source_object_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SAMenu",
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
                ("translation_key", models.UUIDField(default=uuid.uuid4, editable=False)),
                (
                    "locale",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="wagtailcore.locale",
                        verbose_name="locale",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("handle", models.CharField(default="analytics", max_length=100)),
                ("short_name", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "SciELO Analytics menu",
                "verbose_name_plural": "SciELO Analytics menus",
                "unique_together": {("translation_key", "locale")},
            },
        ),
        migrations.CreateModel(
            name="SAMenuItem",
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
                ("label", models.CharField(max_length=255)),
                ("short_label", models.CharField(blank=True, max_length=100)),
                (
                    "item_type",
                    models.CharField(
                        choices=[("page", "Page"), ("url", "URL"), ("anchor", "Anchor")],
                        default="page",
                        max_length=20,
                    ),
                ),
                ("link_url", models.CharField(blank=True, max_length=500)),
                ("link_anchor", models.CharField(blank=True, max_length=255)),
                ("allow_subnav", models.BooleanField(default=False)),
                ("open_in_new_tab", models.BooleanField(default=False)),
                ("is_visible", models.BooleanField(default=True)),
                ("icon_key", models.CharField(blank=True, max_length=100)),
                ("icon_svg", models.TextField(blank=True)),
                (
                    "link_page",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "menu",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="menu_items",
                        to="core.samenu",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="child_menu_items",
                        to="core.samenuitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "SciELO Analytics menu item",
                "verbose_name_plural": "SciELO Analytics menu items",
            },
        ),
        migrations.AddConstraint(
            model_name="samenu",
            constraint=models.UniqueConstraint(
                fields=("locale", "handle"),
                name="core_samenu_unique_handle_locale",
            ),
        ),
        migrations.AddConstraint(
            model_name="samenuitem",
            constraint=models.CheckConstraint(
                condition=~models.Q(parent=models.F("pk")),
                name="core_samenuitem_parent_not_self",
            ),
        ),
    ]
