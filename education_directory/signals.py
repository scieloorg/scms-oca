from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from education_directory.models import EducationDirectory
from education_directory.scripts.index_opensearch import (
    delete_education_instance,
    index_education_instance,
)


def _sync_education_instance(instance):
    if instance.record_status == "PUBLISHED":
        index_education_instance(instance=instance)
        return
    delete_education_instance(instance_id=instance.id)


@receiver(post_save, sender=EducationDirectory)
def sync_education_on_save(sender, instance, **kwargs):
    _sync_education_instance(instance)


@receiver(post_delete, sender=EducationDirectory)
def delete_education_on_delete(sender, instance, **kwargs):
    delete_education_instance(instance_id=instance.id)


@receiver(m2m_changed, sender=EducationDirectory.institutions.through)
def sync_education_on_institutions_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_education_instance(instance)


@receiver(m2m_changed, sender=EducationDirectory.locations.through)
def sync_education_on_locations_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_education_instance(instance)


@receiver(m2m_changed, sender=EducationDirectory.thematic_areas.through)
def sync_education_on_thematic_areas_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_education_instance(instance)
