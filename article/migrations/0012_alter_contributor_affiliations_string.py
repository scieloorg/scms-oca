# Generated by Django 4.1.6 on 2023-07-18 17:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0011_contributor_affiliations_string"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contributor",
            name="affiliations_string",
            field=models.TextField(
                blank=True, null=True, verbose_name="Affiliations_string"
            ),
        ),
    ]
