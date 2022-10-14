# Generated by Django 3.2.12 on 2022-10-14 17:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles_directory', '0002_auto_20221013_1239'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='affiliations',
            name='names',
        ),
        migrations.AddField(
            model_name='affiliations',
            name='name',
            field=models.CharField(blank=True, max_length=510, null=True, verbose_name='Declared Name'),
        ),
        migrations.AddField(
            model_name='affiliations',
            name='source',
            field=models.CharField(blank=True, max_length=510, null=True, verbose_name='Origem'),
        ),
        migrations.RemoveField(
            model_name='contributors',
            name='affiliation',
        ),
        migrations.AddField(
            model_name='contributors',
            name='affiliation',
            field=models.ManyToManyField(blank=True, to='articles_directory.Affiliations'),
        ),
        migrations.DeleteModel(
            name='DeclaredNames',
        ),
    ]