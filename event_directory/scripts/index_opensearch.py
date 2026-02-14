from django.conf import settings

from core.scripts.opensearch_directory_indexer import (
    build_common_directory_doc,
    delete_directory_instance,
    index_directory_instance,
    index_queryset_to_opensearch,
    parse_script_args,
    to_iso,
)
from event_directory.models import EventDirectory


def build_event_doc(obj):
    doc = build_common_directory_doc(
        obj,
        directory_type="diretório de evento",
        scope_label="Evento",
        source_value=str(obj.action) if obj.action else None,
        related_manager_attr="organization",
        related_names_field=None,
        geo_manager_attr="locations",
        geo_location_attr=None,
    )
    doc.update(
        {
            "organization": [org.name for org in obj.organization.all()],
            "start_date": to_iso(obj.start_date),
            "end_date": to_iso(obj.end_date),
            "start_time": to_iso(obj.start_time),
            "end_time": to_iso(obj.end_time),
            "attendance": obj.attendance,
        }
    )
    return doc


def get_event_index_name(index_name=None):
    return index_name or getattr(settings, "OP_INDEX_SOC_PROD", None)


def index_event_instance(instance, index_name=None, refresh=True):
    index_directory_instance(
        instance=instance,
        index_name=get_event_index_name(index_name=index_name),
        build_doc_fn=build_event_doc,
        refresh=refresh,
    )


def delete_event_instance(instance_id, index_name=None, refresh=True):
    delete_directory_instance(
        instance_id=instance_id,
        index_name=get_event_index_name(index_name=index_name),
        refresh=refresh,
    )


def run(*args):
    index_name, batch_size, refresh = parse_script_args(args)
    if not index_name:
        print(
            "Uso: python manage.py runscript index_opensearch --script-args <index_name> [batch_size] [refresh_true_false]"
        )
        return

    objects = EventDirectory.objects.filter(record_status="PUBLISHED")
    index_queryset_to_opensearch(
        objects=objects,
        index_name=index_name,
        build_doc_fn=build_event_doc,
        batch_size=batch_size,
        refresh=refresh,
    )
