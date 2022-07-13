from scholarly_articles import models

import json


def run():
    data = (list(json.loads(x) for x in open('scholarly_articles/scripts/examples.json')))
    for row in data:
        contributor = models.Contributors.objects.get(orcid='0000-0002-4313-1997')
        message = models.ScholarlyArticles.objects.create(
            doi=row['doi'],
            doi_url=row['doi_url'],
            resource_type=row['genre'],
            is_oa=row['is_oa'],
            journal_is_in_doaj=row['journal_is_in_doaj'],
            journal_issns=row['journal_issns'],
            journal_issn_l=row['journal_issn_l'],
            journal_name=row['journal_name'],
            oa_status=row['oa_status'],
            published_date=row['published_date'],
            publisher=row['publisher'],
            title=row['title'],
            update=row['updated'],
            year=row['year'],
            article_json=str(row),
        )
        message.contributors.add(contributor)
