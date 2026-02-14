from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from infrastructure_directory.models import InfrastructureDirectory
from infrastructure_directory.scripts.index_opensearch import (
    delete_infrastructure_instance,
    index_infrastructure_instance,
)


@receiver(post_save, sender=InfrastructureDirectory)
def sync_infrastructure_on_save(sender, instance, **kwargs):
    index_infrastructure_instance(instance=instance)


@receiver(post_delete, sender=InfrastructureDirectory)
def delete_infrastructure_on_delete(sender, instance, **kwargs):
    delete_infrastructure_instance(instance_id=instance.id)


@receiver(m2m_changed, sender=InfrastructureDirectory.institutions.through)
def sync_infrastructure_on_institutions_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        index_infrastructure_instance(instance=instance)


@receiver(m2m_changed, sender=InfrastructureDirectory.thematic_areas.through)
def sync_infrastructure_on_thematic_areas_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        index_infrastructure_instance(instance=instance)
