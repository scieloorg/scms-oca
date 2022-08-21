# Generated by Django 3.2.12 on 2022-08-17 15:42

from django.db import migrations
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0004_alter_taggeditem_content_type_alter_taggeditem_tag'),
        ('education_directory', '0007_educationdirectory_thematic_areas'),
    ]

    operations = [
        migrations.AddField(
            model_name='educationdirectory',
            name='keywords',
            field=taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags'),
        ),
    ]