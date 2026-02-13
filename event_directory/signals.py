from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from event_directory.models import EventDirectory
from event_directory.scripts.index_opensearch import (
    delete_event_instance,
    index_event_instance,
)


def _sync_event_instance(instance):
    if instance.record_status == "PUBLISHED":
        index_event_instance(instance=instance)
        return
    delete_event_instance(instance_id=instance.id)


@receiver(post_save, sender=EventDirectory)
def sync_event_on_save(sender, instance, **kwargs):
    _sync_event_instance(instance)


@receiver(post_delete, sender=EventDirectory)
def delete_event_on_delete(sender, instance, **kwargs):
    delete_event_instance(instance_id=instance.id)


@receiver(m2m_changed, sender=EventDirectory.organization.through)
def sync_event_on_organization_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_event_instance(instance)


@receiver(m2m_changed, sender=EventDirectory.locations.through)
def sync_event_on_locations_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_event_instance(instance)


@receiver(m2m_changed, sender=EventDirectory.thematic_areas.through)
def sync_event_on_thematic_areas_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _sync_event_instance(instance)
