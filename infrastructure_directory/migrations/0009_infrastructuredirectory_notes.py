# Generated by Django 4.1.6 on 2023-05-08 19:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "infrastructure_directory",
            "0008_alter_infrastructuredirectory_institutional_contribution",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="infrastructuredirectory",
            name="notes",
            field=models.TextField(
                blank=True, max_length=1000, null=True, verbose_name="Notes"
            ),
        ),
    ]
