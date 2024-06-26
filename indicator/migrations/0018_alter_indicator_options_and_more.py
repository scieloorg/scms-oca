# Generated by Django 4.1.6 on 2023-05-08 20:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indicator", "0017_alter_indicator_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="indicator",
            options={
                "permissions": (
                    ("must_be_moderate", "Must be moderated"),
                    ("can_edit_record_status", "Can edit record_status"),
                    ("can_edit_action_and_practice", "Can edit action_and_practice"),
                    ("can_edit_link", "Can edit link"),
                    ("can_edit_measurement", "Can edit measurement"),
                    ("can_edit_object_name", "Can edit object_name"),
                    ("can_edit_category", "Can edit category"),
                    ("can_edit_context", "Can edit context"),
                    ("can_edit_scope", "Can edit scope"),
                    ("can_edit_seq", "Can edit seq"),
                    ("can_edit_source", "Can edit source"),
                    ("can_edit_start_date_year", "Can edit start_date_year"),
                    ("can_edit_end_date_year", "Can edit end_date_year"),
                    ("can_edit_validity", "Can edit validity"),
                    ("can_edit_code", "Can edit code"),
                    ("can_edit_thematic_areas", "Can edit thematic_areas"),
                    ("can_edit_locations", "Can edit locations"),
                    ("can_edit_raw_datas", "Can edit raw_datas"),
                    ("can_edit_summarized", "Can edit summarized"),
                    ("can_edit_link_to_data", "Can edit link to data"),
                    ("can_edit_link_to_graphic", "Can edit link do graphic"),
                    ("can_edit_notes", "Can edit notes"),
                )
            },
        ),
        migrations.AddField(
            model_name="indicator",
            name="institutional_contribution",
            field=models.CharField(
                default="SciELO",
                help_text="Name of the contributing institution, default=SciELO.",
                max_length=255,
                verbose_name="Institutional Contribution",
            ),
        ),
        migrations.AddField(
            model_name="indicator",
            name="notes",
            field=models.TextField(
                blank=True, max_length=1000, null=True, verbose_name="Notes"
            ),
        ),
    ]
