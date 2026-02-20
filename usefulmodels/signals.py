from django.db.models.signals import post_save
from django.dispatch import receiver

from education_directory.models import EducationDirectory
from education_directory.scripts.index_opensearch import (
    delete_education_instance,
    index_education_instance,
)
from event_directory.models import EventDirectory
from event_directory.scripts.index_opensearch import (
    delete_event_instance,
    index_event_instance,
)
from infrastructure_directory.models import InfrastructureDirectory
from infrastructure_directory.scripts.index_opensearch import index_infrastructure_instance
from policy_directory.models import PolicyDirectory
from policy_directory.scripts.index_opensearch import (
    delete_policy_instance,
    index_policy_instance,
)

from .models import ThematicArea

@receiver(post_save, sender=ThematicArea)
def sync_related_directories_on_thematic_area_save(sender, instance, created, **kwargs):
    if created:
        return

    for policy in PolicyDirectory.objects.filter(thematic_areas=instance).iterator():
        index_policy_instance(instance=policy)

    for event in EventDirectory.objects.filter(thematic_areas=instance).iterator():
        index_policy_instance(instance=event)

    for education in EducationDirectory.objects.filter(
        thematic_areas=instance
    ).iterator():
        index_policy_instance(instance=education)

    for infrastructure in InfrastructureDirectory.objects.filter(
        thematic_areas=instance
    ).iterator():
        index_infrastructure_instance(instance=infrastructure)
