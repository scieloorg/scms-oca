from scholarly_articles import tasks


def run():
    # atribui affiliation.official e/ou affiliation.country
    # tasks.complete_affiliation_data.apply_async()
    from scholarly_articles.unpaywall import affiliation

    affiliation.complete_affiliation_data()
