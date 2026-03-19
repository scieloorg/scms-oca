import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0001_initial"),
        ("search_gateway", "0002_datasource_field_settings_delete_settingsfilter"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchpage",
            name="data_source",
            field=models.ForeignKey(
                blank=True,
                help_text="Fonte de dados OpenSearch associada a esta página de busca.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="search_pages",
                to="search_gateway.datasource",
                verbose_name="Data Source",
            ),
        ),
    ]
