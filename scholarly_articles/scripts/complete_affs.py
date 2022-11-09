from . import tasks


def run():
    # atribui affiliation.official e/ou affiliation.country
    tasks.complete_affiliation_data.apply_async()
