# Generated by Django 4.1.6 on 2025-06-02 02:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("freepage", "0003_rename_embed_dash_freepage_embed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="freepage",
            name="use_only_embed",
            field=models.BooleanField(
                default=False,
                help_text="If checked, the page will only display the embed content without the body text.",
                verbose_name="Set only embed",
            ),
        ),
    ]
