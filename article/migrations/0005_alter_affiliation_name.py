# Generated by Django 4.1.6 on 2023-07-16 22:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0004_alter_affiliation_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="affiliation",
            name="name",
            field=models.CharField(
                blank=True, max_length=2048, null=True, verbose_name="Nome de afiliação"
            ),
        ),
    ]