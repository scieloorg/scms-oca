# Generated by Django 4.1.6 on 2023-07-16 21:33

from django.db import migrations, models
import django.db.models.deletion
import infrastructure_directory.models


class Migration(migrations.Migration):

    dependencies = [
        ("usefulmodels", "0012_alter_action_creator_alter_action_updated_by_and_more"),
        ("infrastructure_directory", "0014_alter_infrastructuredirectory_action"),
    ]

    operations = [
        migrations.AlterField(
            model_name="infrastructuredirectory",
            name="action",
            field=models.ForeignKey(
                blank=True,
                default=infrastructure_directory.models.get_default_action,
                help_text="",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="usefulmodels.action",
                verbose_name="Ação",
            ),
        ),
    ]
