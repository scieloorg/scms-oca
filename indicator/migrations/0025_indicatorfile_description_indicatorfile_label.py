# Generated by Django 4.1.6 on 2024-09-13 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indicator", "0024_indicatordata"),
    ]

    operations = [
        migrations.AddField(
            model_name="indicatorfile",
            name="description",
            field=models.TextField(
                blank=True, max_length=1024, null=True, verbose_name="Descrição"
            ),
        ),
        migrations.AddField(
            model_name="indicatorfile",
            name="label",
            field=models.CharField(
                blank=True, max_length=1024, null=True, verbose_name="Label"
            ),
        ),
    ]
