# Generated by Django 3.2.12 on 2022-08-25 15:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('education_directory', '0012_alter_educationdirectory_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='educationdirectory',
            name='pratice',
        ),
    ]