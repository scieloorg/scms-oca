# Generated by Django 3.2.12 on 2022-10-21 17:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scholarly_articles', '0004_affiliations_source'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='affiliations',
            name='source',
        ),
    ]