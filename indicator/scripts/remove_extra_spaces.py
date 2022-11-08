from infrastructure_directory.models import InfrastructureDirectory
from event_directory.models import EventDirectory
from education_directory.models import EducationDirectory
from policy_directory.models import PolicyDirectory


def fix():
    for model in (InfrastructureDirectory, EducationDirectory, EventDirectory, PolicyDirectory):
        for item in model.objects.filter(classification__endswith=' ').iterator():
            item.classification = item.classification.strip()
            item.updated_by = item.creator
            item.save()


def run():
    fix()
