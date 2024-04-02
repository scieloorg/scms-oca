# Generated by Django 4.1.6 on 2024-03-28 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indicator", "0021_alter_indicatorfile_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="indicatorfile",
            name="data_ids",
        ),
        migrations.RemoveField(
            model_name="indicator",
            name="indicator_file",
        ),
        migrations.AddField(
            model_name="indicator",
            name="indicator_file",
            field=models.ManyToManyField(
                blank=True, to="indicator.indicatorfile", verbose_name="Indicator File"
            ),
        ),
    ]