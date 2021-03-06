# Generated by Django 3.2.12 on 2022-06-25 21:34

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Contributor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doi', models.CharField(max_length=255, verbose_name='DOI')),
                ('doi_url', models.URLField(max_length=255, verbose_name='DOI URL')),
                ('family', models.CharField(max_length=255, verbose_name='Family')),
                ('given', models.CharField(max_length=255, verbose_name='Given')),
                ('orcid', models.URLField(max_length=255, verbose_name='ORCID')),
                ('authenticated_orcid', models.BooleanField(max_length=255, verbose_name='Authenticated')),
                ('affiliation', models.CharField(max_length=255, verbose_name='Affiliation')),
            ],
        ),
        migrations.CreateModel(
            name='ScholarlyArticles',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doi', models.CharField(max_length=255, verbose_name='DOI')),
                ('doi_url', models.URLField(max_length=255, verbose_name='DOI URL')),
                ('genre', models.CharField(choices=[('', ''), ('Book Section', 'book-section'), ('Monograph', 'monograph'), ('Report', 'report'), ('Peer Review', 'peer-review'), ('Book Track', 'book-track'), ('Journal Article', 'journal-article'), ('Part', 'book-part'), ('Other', 'other'), ('Book', 'book'), ('Journal Volume', 'journal-volume'), ('Book Set', 'book-set'), ('Reference Entry', 'reference-entry'), ('Proceedings Article', 'proceedings-article'), ('Journal', 'journal'), ('component', 'Component'), ('Book Chapter', 'book-chapter'), ('Proceedings Series', 'proceedings-series'), ('Report Series', 'report-series'), ('Proceedings', 'proceedings'), ('Standard', 'standard'), ('Reference Book', 'reference-book'), ('Posted Content', 'posted-content'), ('Journal Issue', 'journal-issue'), ('Dissertation', 'dissertation'), ('Grant', 'grant'), ('Dataset', 'dataset'), ('Book Series', 'book-series'), ('Edited Book', 'edited-book'), ('Standard Series', 'standard-series')], max_length=255, verbose_name='Resource Type')),
                ('is_oa', models.BooleanField(max_length=255, verbose_name='Opens Access')),
                ('journal_is_in_doaj', models.BooleanField(max_length=255, verbose_name='DOAJ')),
                ('journal_issns', models.CharField(max_length=255, verbose_name="ISSN's")),
                ('journal_issn_l', models.CharField(max_length=255, verbose_name='ISSN-L')),
                ('journal_name', models.CharField(max_length=255, verbose_name='Journal Name')),
                ('published_date', models.DateTimeField(max_length=255, verbose_name='Published Date')),
                ('publisher', models.CharField(max_length=255, verbose_name='Publisher')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
            ],
        ),
    ]
