import os
from scholarly_articles import models
from django.contrib.auth import get_user_model

from usefulmodels.models import Country


User = get_user_model()

SEPARATOR = ';'

def get_country(country):
    return models.Affiliations.objects.filter(name__icontains=country, country__isnull=True)


def run(*args):
    user_id = 1

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/countries.csv", 'r') as fp:
        for line in fp.readlines():
            name_pt, name_en, capital, acron3, acron2 = line.strip().split(SEPARATOR)

            # User
            if args:
                user_id = args[0]

            creator = User.objects.get(id=user_id)

            search_for = [name_pt, name_en]
            for pos in range(len(search_for)):
                affiliations = get_country(search_for[pos])
                for affiliation in affiliations.iterator():
                    affiliation.country = Country.get_or_create(user=creator, name_pt=search_for[pos]) \
                        if pos == 0 \
                        else Country.get_or_create(user=creator, name_en=search_for[pos])
                    affiliation.save()
