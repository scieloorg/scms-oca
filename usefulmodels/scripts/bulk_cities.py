import os
from usefulmodels import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of cities
# This presuppose a fixtures/cities.csv file exists.
# Consider that existe a user with id=1


def run(): 
    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/cities.csv", 'r') as fp:
        for line in fp.readlines():
            name = line.strip()

            # User
            creator = User.objects.get(id=1)

            models.City(name=name, creator=creator).save()
