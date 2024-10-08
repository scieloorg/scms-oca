# Generated by Django 4.1.6 on 2023-07-18 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0008_remove_affiliation_article_aff_name_d033b1_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="affiliation",
            name="name",
            field=models.CharField(
                blank=True, max_length=2048, null=True, verbose_name="Nome de afiliação"
            ),
        ),
        migrations.AddIndex(
            model_name="affiliation",
            index=models.Index(fields=["name"], name="article_aff_name_d033b1_idx"),
        ),
    ]
