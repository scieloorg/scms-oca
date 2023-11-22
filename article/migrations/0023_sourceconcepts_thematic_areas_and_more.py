# Generated by Django 4.1.6 on 2023-10-30 08:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usefulmodels", "0012_alter_action_creator_alter_action_updated_by_and_more"),
        ("article", "0022_alter_sourceconcepts_parent_display_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourceconcepts",
            name="thematic_areas",
            field=models.ManyToManyField(
                blank=True,
                help_text="Thematic area relation",
                to="usefulmodels.thematicarea",
                verbose_name="Área temática",
            ),
        ),
        migrations.AlterField(
            model_name="sourceconcepts",
            name="parent_ids",
            field=models.ManyToManyField(
                blank=True,
                help_text="Parent relation",
                related_name="parent_id",
                to="article.sourceconcepts",
                verbose_name="Parent ids",
            ),
        ),
    ]