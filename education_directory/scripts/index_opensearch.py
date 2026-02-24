import logging

from django.conf import settings
from core.scripts.opensearch_directory_indexer import (
    build_common_directory_doc,
    delete_directory_instance,
    index_directory_instance,
    index_queryset_to_opensearch,
    parse_script_args,
    to_iso,
)
from education_directory.models import EducationDirectory
from search_gateway.client import get_opensearch_client


logger = logging.getLogger(__name__)


def get_education_index_name(index_name=None):
    return index_name or getattr(settings, "OP_INDEX_SOC_PROD", None)


def build_education_doc(obj):
    doc = build_common_directory_doc(
        obj,
        directory_type="diretório de educação",
        scope_label="Educação",
        source_value=str(obj.action) if obj.action else None,
        related_manager_attr="institutions",
        geo_manager_attr="locations",
        geo_location_attr=None,
    )
    doc.update(
        {
            "start_date": to_iso(obj.start_date),
            "start_date_year": getattr(obj.start_date, "year", None),
            "end_date": to_iso(obj.end_date),
            "end_date_year": getattr(obj.end_date, "year", None),
            "start_time": to_iso(obj.start_time),
            "end_time": to_iso(obj.end_time),
        }
    )
    return doc


def index_education_instance(instance, index_name=None, refresh=True):
    index_directory_instance(
        instance=instance,
        index_name=get_education_index_name(index_name=index_name),
        build_doc_fn=build_education_doc,
        refresh=refresh,
    )


def delete_education_instance(instance_id, index_name=None, refresh=True):
    delete_directory_instance(
        instance_id=instance_id,
        index_name=get_education_index_name(index_name=index_name),
        refresh=refresh,
    )


def run(*args):
    index_name, batch_size, refresh = parse_script_args(args)
    if not index_name:
        print(
            "Uso: python manage.py runscript index_opensearch --script-args <index_name> [batch_size] [refresh_true_false]"
        )
        return
    objects = EducationDirectory.objects.filter(record_status="PUBLISHED")
    index_queryset_to_opensearch(
        objects=objects,
        index_name=index_name,
        build_doc_fn=build_education_doc,
        batch_size=batch_size,
        refresh=refresh,
    )
