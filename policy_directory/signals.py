from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from policy_directory.models import PolicyDirectory
from policy_directory.scripts.index_opensearch import (
    delete_policy_instance,
    index_policy_instance,
)


def _sync_policy_instance(instance):
    if instance.record_status == "PUBLISHED":
        index_policy_instance(instance=instance)
        return
    delete_policy_instance(instance_id=instance.id)


@receiver(post_save, sender=PolicyDirectory)
def sync_policy_on_save(sender, instance, **kwargs):
    _sync_policy_instance(instance)


@receiver(post_delete, sender=PolicyDirectory)
def delete_policy_on_delete(sender, instance, **kwargs):
    delete_policy_instance(instance_id=instance.id)


@receiver(m2m_changed, sender=PolicyDirectory.institutions.through)
def sync_policy_on_institutions_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_policy_instance(instance)


@receiver(m2m_changed, sender=PolicyDirectory.thematic_areas.through)
def sync_policy_on_thematic_areas_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_policy_instance(instance)
