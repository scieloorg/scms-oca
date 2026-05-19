# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("etl", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="etlpipelineconfig",
            name="silver_index_pattern",
        ),
    ]
