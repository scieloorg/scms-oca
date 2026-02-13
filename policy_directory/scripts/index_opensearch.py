from django.conf import settings

from core.scripts.opensearch_directory_indexer import (
    build_common_directory_doc,
    delete_directory_instance,
    index_directory_instance,
    index_queryset_to_opensearch,
    parse_script_args,
    to_iso,
)
from policy_directory.models import PolicyDirectory


def build_policy_doc(obj):
    doc = build_common_directory_doc(
        obj,
        directory_type="diretório de politica",
        scope_label="Politica",
        source_value=str(obj.action) if obj.action else None,
        related_manager_attr="institutions",
        include_disclaimer=False,
    )
    doc.update(
        {
            "date": to_iso(obj.date),
        }
    )
    return doc


def get_policy_index_name(index_name=None):
    return index_name or getattr(settings, "OP_INDEX_SOC_PROD", None)


def index_policy_instance(instance, index_name=None, refresh=True):
    index_directory_instance(
        instance=instance,
        index_name=get_policy_index_name(index_name=index_name),
        build_doc_fn=build_policy_doc,
        refresh=refresh,
    )


def delete_policy_instance(instance_id, index_name=None, refresh=True):
    delete_directory_instance(
        instance_id=instance_id,
        index_name=get_policy_index_name(index_name=index_name),
        refresh=refresh,
    )


def run(*args):
    index_name, batch_size, refresh = parse_script_args(args)
    if not index_name:
        print(
            "Uso: python manage.py runscript index_opensearch --script-args <index_name> [batch_size] [refresh_true_false]"
        )
        return

    objects = PolicyDirectory.objects.filter(record_status="PUBLISHED")
    index_queryset_to_opensearch(
        objects=objects,
        index_name=index_name,
        build_doc_fn=build_policy_doc,
        batch_size=batch_size,
        refresh=refresh,
    )
