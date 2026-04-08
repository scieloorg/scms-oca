from django.db.models.signals import post_delete, post_save, pre_delete
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
from infrastructure_directory.scripts.index_opensearch import (
    delete_infrastructure_instance,
    index_infrastructure_instance,
)
from policy_directory.models import PolicyDirectory
from policy_directory.scripts.index_opensearch import (
    delete_policy_instance,
    index_policy_instance,
)

from .models import ThematicArea


def _reindex_related_directories(*, policy_ids, event_ids, education_ids, infrastructure_ids):
    for policy in PolicyDirectory.objects.filter(id__in=policy_ids).iterator():
        if policy.record_status == "PUBLISHED":
            index_policy_instance(instance=policy)
        else:
            delete_policy_instance(instance_id=policy.id)

    for event in EventDirectory.objects.filter(id__in=event_ids).iterator():
        if event.record_status == "PUBLISHED":
            index_event_instance(instance=event)
        else:
            delete_event_instance(instance_id=event.id)

    for education in EducationDirectory.objects.filter(id__in=education_ids).iterator():
        if education.record_status == "PUBLISHED":
            index_education_instance(instance=education)
        else:
            delete_education_instance(instance_id=education.id)

    for infrastructure in InfrastructureDirectory.objects.filter(
        id__in=infrastructure_ids
    ).iterator():
        if infrastructure.record_status == "PUBLISHED":
            index_infrastructure_instance(instance=infrastructure)
        else:
            delete_infrastructure_instance(instance_id=infrastructure.id)


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
