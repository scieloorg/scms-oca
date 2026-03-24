from django.db import migrations

from search_gateway.migrations._field_settings_snapshot import build_canonical_field_settings
from search_gateway.migrations._field_settings_snapshot import unwrap_field_settings


def forward_populate_field_settings_schema(apps, schema_editor):
    DataSource = apps.get_model("search_gateway", "DataSource")

    for data_source in DataSource.objects.all():
        data_source.field_settings = build_canonical_field_settings(
            data_source.index_name,
            data_source.field_settings or {},
        )
        data_source.save(update_fields=["field_settings"])


def backward_unwrap_field_settings_schema(apps, schema_editor):
    DataSource = apps.get_model("search_gateway", "DataSource")

    for data_source in DataSource.objects.all():
        data_source.field_settings = unwrap_field_settings(data_source.field_settings or {})
        data_source.save(update_fields=["field_settings"])


class Migration(migrations.Migration):

    dependencies = [
        ("search_gateway", "0002_datasource_field_settings_delete_settingsfilter"),
    ]

    operations = [
        migrations.RunPython(
            forward_populate_field_settings_schema,
            backward_unwrap_field_settings_schema,
        ),
    ]
