import os
from scholarly_articles import models
from django.contrib.auth import get_user_model

User = get_user_model()

SEPARATOR = ';'

def get_country(country):
    return models.Affiliations.objects.filter(name__icontains=country)


def run(*args):
    user_id = 1

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/countries.csv", 'r') as fp:
        for line in fp.readlines():
            name_pt, name_en, capital, acron3, acron2 = line.strip().split(SEPARATOR)

            # User
            if args:
                user_id = args[0]

            creator = User.objects.get(id=user_id)

            for country in [name_pt, name_en]:
                affiliations = get_country(country)
                for affiliation in affiliations.iterator():
                    if not affiliation.country:
                        affiliation.country = name_pt
                        affiliation.save()
