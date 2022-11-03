import csv
import os

from django.contrib.auth import get_user_model

from config import celery_app
from institution.scripts import bulk_institution

User = get_user_model()

@celery_app.task()
def load_official_institution(user_id):
    """
    Load the data from a CSV file.

    Sync or Async function

    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    for item in [['mec', ';', 'MEC'], ['ror', ',', 'ROR']]:
        with open(os.path.dirname(os.path.realpath(__file__)) + f"/fixtures/institutions_{item[0]}.csv", 'r') as csvfile:
            data = csv.DictReader(csvfile, delimiter=item[1])

            for line, row in enumerate(data):
                bulk_institution.load_official_institution(creator=user, row=row, line=line, source=item[2])