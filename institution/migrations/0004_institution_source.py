# Generated by Django 3.2.12 on 2022-10-21 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('institution', '0003_alter_institution_institution_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='institution',
            name='source',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Institution Source'),
        ),
    ]