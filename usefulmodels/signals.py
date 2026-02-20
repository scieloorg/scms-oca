from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from education_directory.models import EducationDirectory
from education_directory.scripts.index_opensearch import index_education_instance
from event_directory.models import EventDirectory
from event_directory.scripts.index_opensearch import index_event_instance
from infrastructure_directory.models import InfrastructureDirectory
from infrastructure_directory.scripts.index_opensearch import index_infrastructure_instance
from policy_directory.models import PolicyDirectory
from policy_directory.scripts.index_opensearch import index_policy_instance

from .models import ThematicArea


def _reindex_related_directories(*, policy_ids, event_ids, education_ids, infrastructure_ids):
    for policy in PolicyDirectory.objects.filter(id__in=policy_ids).iterator():
        index_policy_instance(instance=policy)

    for event in EventDirectory.objects.filter(id__in=event_ids).iterator():
        index_event_instance(instance=event)

    for education in EducationDirectory.objects.filter(id__in=education_ids).iterator():
        index_education_instance(instance=education)

    for infrastructure in InfrastructureDirectory.objects.filter(
        id__in=infrastructure_ids
    ).iterator():
        index_infrastructure_instance(instance=infrastructure)


@receiver(post_save, sender=ThematicArea)
def sync_related_directories_on_thematic_area_save(sender, instance, created, **kwargs):
    if created:
        return

    _reindex_related_directories(
        policy_ids=PolicyDirectory.objects.filter(thematic_areas=instance).values_list(
            "id", flat=True
        ),
        event_ids=EventDirectory.objects.filter(thematic_areas=instance).values_list(
            "id", flat=True
        ),
        education_ids=EducationDirectory.objects.filter(
            thematic_areas=instance
        ).values_list("id", flat=True),
        infrastructure_ids=InfrastructureDirectory.objects.filter(
            thematic_areas=instance
        ).values_list("id", flat=True),
    )


@receiver(pre_delete, sender=ThematicArea)
def cache_related_directories_before_thematic_area_delete(sender, instance, **kwargs):
    instance._related_directory_ids = {
        "policy_ids": list(
            PolicyDirectory.objects.filter(thematic_areas=instance).values_list(
                "id", flat=True
            )
        ),
        "event_ids": list(
            EventDirectory.objects.filter(thematic_areas=instance).values_list(
                "id", flat=True
            )
        ),
        "education_ids": list(
            EducationDirectory.objects.filter(thematic_areas=instance).values_list(
                "id", flat=True
            )
        ),
        "infrastructure_ids": list(
            InfrastructureDirectory.objects.filter(thematic_areas=instance).values_list(
                "id", flat=True
            )
        ),
    }


@receiver(post_delete, sender=ThematicArea)
def sync_related_directories_on_thematic_area_delete(sender, instance, **kwargs):
    related_ids = getattr(instance, "_related_directory_ids", None)
    if not related_ids:
        return

    _reindex_related_directories(**related_ids)