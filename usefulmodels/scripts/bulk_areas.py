import os
from usefulmodels import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of thematic areas
# Consider that exist a user with id=1

SEPARATOR = ';'

def run(*args):
    user_id = 1

    # Delete all thematic areas
    models.ThematicArea.objects.all().delete()

    # User
    if args:
        user_id = args[0]

    creator = User.objects.get(id=user_id)

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/thematic_areas.csv", 'r') as fp:
        for line in fp.readlines():
            level0, level1, level2 = line.strip().split(SEPARATOR)

            models.ThematicArea(level0=level0, level1=level1, level2=level2, creator=creator).save()
