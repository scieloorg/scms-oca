from django.core.exceptions import FieldError

from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory

import csv
import os


def check_values():
    models = (EducationDirectory, EventDirectory, InfrastructureDirectory, PolicyDirectory)
    fields = ('locations', 'institutions', 'attendance', 'description')
    d = []
    for model in models:
        for field in fields:
            try:
                if field == 'locations':
                    records = model.objects.filter(locations=None)
                elif field == 'institutions':
                    records = model.objects.filter(institutions=None)
                elif field == 'attendance':
                    records = model.objects.filter(attendance=None)
                else:
                    records = model.objects.filter(description=None)
                for item in records.iterator():
                    d.append(
                        {'model': model.__name__,
                         'field_missing': field,
                         'register_id': item.id,
                         'register_text': item.__str__()
                         }
                    )
            except FieldError:
                pass

    with open(os.path.dirname(os.path.realpath(__file__)) + "/./fixtures/missing_values.csv", 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['model', 'field_missing', 'register_id', 'register_text'])
        writer.writeheader()
        writer.writerows(d)
