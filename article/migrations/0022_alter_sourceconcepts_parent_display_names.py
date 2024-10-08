# Generated by Django 4.1.6 on 2023-10-30 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0021_alter_sourceconcepts_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sourceconcepts",
            name="parent_display_names",
            field=models.CharField(
                blank=True,
                help_text="The name of parents up to child names",
                max_length=512,
                null=True,
                verbose_name="Parent Display Name",
            ),
        ),
    ]
