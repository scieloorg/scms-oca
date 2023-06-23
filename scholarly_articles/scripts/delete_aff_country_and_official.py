from scholarly_articles import tasks


def run():
    tasks.delete_aff_country_and_official.apply_async()
