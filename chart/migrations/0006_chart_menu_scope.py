# Generated by Django 4.1.6 on 2025-07-31 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chart", "0005_chart_link_chart"),
    ]

    operations = [
        migrations.AddField(
            model_name="chart",
            name="menu_scope",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Escopo do menu"
            ),
        ),
    ]
