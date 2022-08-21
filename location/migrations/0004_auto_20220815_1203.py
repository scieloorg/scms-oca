# Generated by Django 3.2.12 on 2022-08-15 12:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usefulmodels', '0004_auto_20220815_1203'),
        ('location', '0003_alter_location_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='sort_order',
            field=models.IntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='city',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='usefulmodels.city', verbose_name='Cidade'),
        ),
        migrations.AlterField(
            model_name='location',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='usefulmodels.country', verbose_name='País'),
        ),
        migrations.AlterField(
            model_name='location',
            name='region',
            field=models.CharField(blank=True, choices=[('', ''), ('Norte', 'Norte'), ('Nordeste', 'Nordeste'), ('Centro-Oeste', 'Centro-Oeste'), ('Sudeste', 'Sudeste'), ('Sul', 'Sul')], max_length=255, null=True, verbose_name='Região'),
        ),
        migrations.AlterField(
            model_name='location',
            name='state',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='usefulmodels.state', verbose_name='Estado'),
        ),
    ]