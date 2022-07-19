from scholarly_articles import models

import json
from datetime import date


def load(row):
    try:
        if row.get('doi'):
            rawunpaywall = models.RawUnpaywall.objects.filter(doi=row['doi'])
            if len(rawunpaywall) == 0:
                rawunpaywall = models.RawUnpaywall()
                rawunpaywall.doi = row['doi']
                rawunpaywall.harvesting_creation = date.today()
            else:
                return
        if row.get('is_paratext'):
            rawunpaywall.is_paratext = row['is_paratext']
        if row.get('year'):
            rawunpaywall.year = row['year']
        if row.get('genre'):
            rawunpaywall.resource_type = row['genre']
        if row.get('updated'):
            rawunpaywall.update = row['updated'][:10]
        rawunpaywall.json = row
        rawunpaywall.save()
    except KeyError:
        pass


def run():
    data = (list(json.loads(x) for x in open('scholarly_articles/scripts/examples.json')))
    for row in data:
        load(row)
