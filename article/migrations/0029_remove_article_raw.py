# Generated by Django 4.1.6 on 2024-03-28 17:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0028_article_raw"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="article",
            name="raw",
        ),
    ]