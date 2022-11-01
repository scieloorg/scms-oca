# Generated by Django 3.2.12 on 2022-10-26 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usefulmodels', '0005_alter_state_region'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='country',
            name='name',
        ),
        migrations.AddField(
            model_name='country',
            name='name_en',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Name of the Country (en)'),
        ),
        migrations.AddField(
            model_name='country',
            name='name_pt',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Name of the Country (pt)'),
        ),
    ]