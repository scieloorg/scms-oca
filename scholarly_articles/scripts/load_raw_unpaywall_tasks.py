from scholarly_articles.tasks import load_unpaywall_row

import json


def run():
    for row in open('scholarly_articles/scripts/examples.json'):
        row = json.loads(row)
        load_unpaywall_row(row)
