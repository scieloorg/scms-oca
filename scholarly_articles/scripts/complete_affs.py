from scholarly_articles import tasks


def run():
    tasks.complete_affiliation_data.apply_async()
