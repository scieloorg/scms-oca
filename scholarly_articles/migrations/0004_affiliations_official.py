# Generated by Django 3.2.12 on 2022-09-07 18:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('institution', '0003_alter_institution_institution_type'),
        ('scholarly_articles', '0003_auto_20220907_1749'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliations',
            name='official',
            field=models.ForeignKey(blank=True, max_length=1020, null=True, on_delete=django.db.models.deletion.SET_NULL, to='institution.institution', verbose_name='Official Affiliation Name'),
        ),
    ]