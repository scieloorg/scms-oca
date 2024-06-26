# Generated by Django 4.1.6 on 2023-05-08 20:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("event_directory", "0007_alter_eventdirectory_record_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventdirectory",
            name="institutional_contribution",
            field=models.CharField(
                default="SciELO",
                help_text="Name of the contributing institution, default=SciELO.",
                max_length=255,
                verbose_name="Institutional Contribution",
            ),
        ),
        migrations.AddField(
            model_name="eventdirectory",
            name="notes",
            field=models.TextField(
                blank=True, max_length=1000, null=True, verbose_name="Notes"
            ),
        ),
    ]
