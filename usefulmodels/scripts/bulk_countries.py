import os
from usefulmodels import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of countries
# This presuppose a fixtures/countries.csv file exists.
# Consider that existe a user with id=1

SEPARATOR = ';'

def run(*args):
    user_id = 1

    # Delete all cities
    models.Country.objects.all().delete()

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/countries.csv", 'r') as fp:
        for line in fp.readlines():
            name_pt, name_en, capital, acron3, acron2 = line.strip().split(SEPARATOR)

            # User
            if args:
                user_id = args[0]

            creator = User.objects.get(id=user_id)

            models.Country(name_pt=name_pt, name_en=name_en, acron3=acron3, acron2=acron2, creator=creator).save()
