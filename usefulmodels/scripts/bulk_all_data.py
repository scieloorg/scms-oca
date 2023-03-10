from . import bulk_cities, bulk_states, bulk_countries, bulk_action, bulk_pratice, bulk_areas
from institution.scripts import bulk_institution


scripts = [bulk_cities, bulk_states, bulk_countries, bulk_action, bulk_pratice, bulk_areas, bulk_institution]

def run(*args):
    for script in scripts:
        script.run(*args)
