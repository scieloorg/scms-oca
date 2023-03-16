from infrastructure_directory.models import InfrastructureDirectory
from event_directory.models import EventDirectory
from education_directory.models import EducationDirectory
from policy_directory.models import PolicyDirectory
from education_directory.choices import classification as education_choices
from event_directory.choices import classification as event_choices
from infrastructure_directory.choices import classification as infra_choices
from policy_directory.choices import classification as policy_choices


def qa():
    classifications = []
    classifications.extend([c[0] for c in education_choices])
    classifications.extend([c[0] for c in event_choices])
    classifications.extend([c[0] for c in infra_choices])
    classifications.extend([c[0] for c in policy_choices])

    for model in (
        EducationDirectory,
        InfrastructureDirectory,
        EventDirectory,
        PolicyDirectory,
    ):
        for item in model.objects.iterator():
            item.record_status = "PUBLISHED"
            alt = []
            for classification in classifications:
                if (
                    classification in item.description.lower()
                    or classification in item.title.lower()
                ):
                    alt.append(classification)
            if alt and item.classification not in alt:
                item.record_status = "TO MODERATE"
            item.save()


def run():
    qa()
