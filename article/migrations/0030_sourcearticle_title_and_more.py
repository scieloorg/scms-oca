# Generated by Django 4.1.6 on 2024-04-01 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0029_remove_article_raw"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcearticle",
            name="title",
            field=models.CharField(max_length=1024, null=True, verbose_name="Título"),
        ),
        migrations.AddIndex(
            model_name="sourcearticle",
            index=models.Index(fields=["title"], name="article_sou_title_96a85d_idx"),
        ),
    ]