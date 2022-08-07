import os
from usefulmodels import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of states
# This presuppose a fixtures/states.csv file exists.
# Consider that existe a user with id=1

SEPARATOR = ','

def run(): 
    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/states.csv", 'r') as fp:
        for line in fp.readlines():
            name, acron = line.strip().split(SEPARATOR)

            # User
            creator = User.objects.get(id=1)

            models.State(name=name, acronym=acron, creator=creator).save()
