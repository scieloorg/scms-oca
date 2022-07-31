from scholarly_articles.scripts.unpaywall import load

import json


def run():
    data = (list(json.loads(x) for x in open('scholarly_articles/scripts/examples.json')))
    for row in data:
        load(row)
