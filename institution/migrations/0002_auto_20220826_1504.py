# Generated by Django 3.2.12 on 2022-08-26 15:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("institution", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="institution",
            name="level_1",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="Level 1 organization",
            ),
        ),
        migrations.AddField(
            model_name="institution",
            name="level_2",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="Level 2 organization",
            ),
        ),
        migrations.AddField(
            model_name="institution",
            name="level_3",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="Level 3 organization",
            ),
        ),
        migrations.AddField(
            model_name="institution",
            name="logo",
            field=models.ImageField(
                blank=True, null=True, upload_to="", verbose_name="Logo"
            ),
        ),
        migrations.AddField(
            model_name="institution",
            name="url",
            field=models.URLField(blank=True, null=True, verbose_name="url"),
        ),
    ]
