"""
Funções responsáveis por indexar os dados brutos (quando disponível o raw_data).
"""

import logging

from django.conf import settings

from search_gateway.client import get_opensearch_client

from .exception_logs import ExceptionContext
from .models import HarvestStatus

logger = logging.getLogger(__name__)


def _get_index_name(model_name=None, instance=None, type_data=None):
    if instance is not None and not model_name:
        model_name = instance.__class__.__name__
    if not model_name:
        return None
    if model_name == "HarvestedSciELOData":
        effective_type = type_data or getattr(instance, "type_data", None)
        index = {
            "dataset":  getattr(
                settings, "OPENSEARCH_INDEX_RAW_SCIELO_DATA_DATASET", None
            ),
            "dataverse": getattr(
                settings, "OPENSEARCH_INDEX_RAW_SCIELO_DATA_DATAVERSE", None
            )
        }
        return index.get(effective_type, None)
    return {
        "HarvestedPreprint": getattr(settings, "OPENSEARCH_INDEX_RAW_PREPRINT", None),
        "HarvestedBooks": getattr(settings, "OPENSEARCH_INDEX_RAW_BOOK", None),
    }.get(model_name)


def _get_error_log_fk_field(instance):
    return {
        "HarvestedPreprint": "preprint",
        "HarvestedBooks": "book",
        "HarvestedSciELOData": "scielo_data",
    }.get(instance.__class__.__name__)


def index_harvested_raw_data(model, index_name=None, only_success=True, refresh=False):
    """
    Indexa o raw_data dos modelos HarvestedPreprint, HarvestedBooks e
    HarvestedSciELOData no OpenSearch.
    """
    status_filter = [HarvestStatus.SUCCESS]
    if not only_success:
        status_filter = None

    queryset = model.objects.all()
    if status_filter:
        queryset = queryset.filter(harvest_status__in=status_filter)
    for obj in queryset.iterator():
        index_name = _get_index_name(model_name=model.__name__, instance=obj)
        index_harvested_instance(instance=obj, index_name=index_name, refresh=False)


def index_harvested_instance(instance, index_name=None, refresh=False):
    """
    Indexa um único objeto harvest no OpenSearch.
    """
    exc_context = ExceptionContext(
        harvest_object=instance,
        log_model=instance.harvest_error_log.model,
        fk_field=_get_error_log_fk_field(instance),
    )
    client = get_opensearch_client()
    if client is None:
        logger.warning("OpenSearch client não configurado.")
        return
    if not index_name:
        logger.warning(
            f"Index name não configurado para {instance.__class__.__name__} ({instance.identifier})."
        )
        return

    try:
        logging.info(
            f"Indexando instancia {instance.__class__.__name__}: {instance.identifier} no indice {index_name}"
        )
        client.index(
            index=index_name,
            id=instance.identifier,
            body={"raw_data": instance.raw_data},
            refresh=False,
        )
        instance.mark_as_indexed(index_name=index_name)
    except Exception as exc:
        logger.warning(
            f"Falha ao indexar em {index_name} {instance.__class__.__name__} ({instance.identifier}): {exc}"
        )
        instance.mark_as_index_failed()
        exc_context.add_exception(exception=exc, field_name="raw_data")
        exc_context.save_to_db()

    if refresh:
        client.indices.refresh(index=index_name)


def delete_harvested_document(model_name, identifier, refresh=False):
    index_name = _get_index_name(model_name=model_name)
    if not index_name:
        logger.warning(f"Index name não configurado para {model_name}.")
        return
    client = get_opensearch_client()
    if client is None:
        logger.warning("OpenSearch client não configurado.")
        return
    try:
        logging.info(f"Removendo documento {identifier} do indice {index_name}")
        client.delete(index=index_name, id=identifier, refresh=refresh)
    except Exception as exc:
        logger.warning(
            f"Falha ao remover em {index_name} ({identifier}): {exc}"
        )
