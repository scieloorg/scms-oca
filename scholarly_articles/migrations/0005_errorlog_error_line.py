# Generated by Django 3.2.12 on 2022-09-12 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scholarly_articles', '0004_affiliations_official'),
    ]

    operations = [
        migrations.AddField(
            model_name='errorlog',
            name='error_line',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Error Line'),
        ),
    ]