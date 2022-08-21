# Generated by Django 3.2.12 on 2022-08-17 18:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usefulmodels', '0011_action_pratice'),
        ('policy_directory', '0005_policydirectory_keywords'),
    ]

    operations = [
        migrations.AddField(
            model_name='policydirectory',
            name='action',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='usefulmodels.action'),
        ),
        migrations.AddField(
            model_name='policydirectory',
            name='classification',
            field=models.CharField(blank=True, choices=[('', ''), ('promoção', 'promoção'), ('posicionamento', 'posicionamento'), ('mandato', 'mandato'), ('geral', 'geral')], max_length=255, null=True, verbose_name='Classification'),
        ),
        migrations.AddField(
            model_name='policydirectory',
            name='pratice',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='usefulmodels.pratice'),
        ),
    ]