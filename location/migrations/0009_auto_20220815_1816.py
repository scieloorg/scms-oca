# Generated by Django 3.2.12 on 2022-08-15 18:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0008_location_institution'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='location',
            name='institution',
        ),
        migrations.RemoveField(
            model_name='location',
            name='name',
        ),
        migrations.RemoveField(
            model_name='location',
            name='sort_order',
        ),
    ]