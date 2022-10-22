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

    with open(os.path.dirname(os.path.realpath(__file__)) + "/fixtures/institutions.csv", 'r') as csvfile:
        data = csv.DictReader(csvfile, delimiter=";")

        for line, row in enumerate(data):
            bulk_institution.load_official_institution(creator=user, row=row, line=line)
