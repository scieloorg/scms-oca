# Generated by Django 4.1.6 on 2023-06-22 20:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indicator", "0018_alter_indicator_options_and_more"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="indicator",
            name="indicator_i_descrip_361176_idx",
        ),
        migrations.RemoveIndex(
            model_name="indicator",
            name="indicator_i_scope_7e501d_idx",
        ),
        migrations.RemoveIndex(
            model_name="indicator",
            name="indicator_i_seq_c68a1b_idx",
        ),
        migrations.RemoveIndex(
            model_name="indicator",
            name="indicator_i_context_564325_idx",
        ),
        migrations.AddIndex(
            model_name="indicator",
            index=models.Index(fields=["slug"], name="indicator_i_slug_1e40c9_idx"),
        ),
    ]