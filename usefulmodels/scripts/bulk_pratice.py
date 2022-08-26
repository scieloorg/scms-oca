
from usefulmodels import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of pratices
# Consider that existe a user with id=1

PRATICES = [
    ('10', 'política, recomendação etc.'),
    ('20', 'desempenho'),
    ('30', 'infraestrutura'),
    ('40', 'educação'),
    ('50', 'divulgação'),
    ('90', 'outras'),
]

def run(*args):
    user_id = 1

    # Delete all pratices
    models.Practice.objects.all().delete()

    # User
    if args:
        user_id = args[0]

    creator = User.objects.get(id=user_id)

    for code, val in PRATICES:

        models.Practice(code=code, name=val, creator=creator).save()
