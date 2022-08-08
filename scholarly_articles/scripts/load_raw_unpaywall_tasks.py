from scholarly_articles.tasks import load_unpaywall_row

import json


def run():
    for row in open('scholarly_articles/scripts/unpaywall_2022.jsonl'):
        load_unpaywall_row(json.loads(row))
