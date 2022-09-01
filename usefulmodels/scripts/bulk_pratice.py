import os
from usefulmodels import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of pratices
# Consider that existe a user with id=1

SEPARATOR = ';'

def run(*args):
    user_id = 1

    # Delete all pratices
    models.Practice.objects.all().delete()

    # User
    if args:
        user_id = args[0]

    creator = User.objects.get(id=user_id)

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/practices.csv", 'r') as fp:
        for line in fp.readlines():
            code, val = line.strip().split(SEPARATOR)

            models.Practice(code=code, name=val, creator=creator).save()
