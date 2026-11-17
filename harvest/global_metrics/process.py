import logging
from pathlib import Path

from django.conf import settings
from django.db import InterfaceError, OperationalError, close_old_connections

from harvest.global_metrics.indexing import GlobalMetricsIndexingError, index_file_obj
from harvest.models import GlobalMetricsUploadFile


def process_global_metrics_upload_file(upload_file_id, index_name=None, chunk_size=None):
    close_old_connections()
    upload_file = GlobalMetricsUploadFile.objects.get(pk=upload_file_id)
    if upload_file.status:
        logging.info(
            f"Arquivo de métricas globais {upload_file.pk} já foi processado; reindexação ignorada."
        )

        return {
            "skipped": True,
            "rows_read": 0,
            "indexed": 0,
            "failed": 0,
            "errors": [],
        }

    target_index = index_name or settings.GLOBAL_METRICS_FILE_UPLOAD_OPENSEARCH_INDEX
    stats = None

    try:
        with upload_file.file.open("rb") as file_obj:
            stats = index_file_obj(
                file_obj=file_obj,
                file_name=Path(upload_file.file.name).name,
                index_name=index_name,
                chunk_size=chunk_size,
            )

        if stats.failed > 0:
            raise GlobalMetricsIndexingError(
                f"Falha ao indexar arquivo de métricas globais {upload_file.pk} em {target_index}: "
                f"{stats.failed} falha(s) em {stats.rows_read} linha(s) lida(s)."
            )

        if stats.rows_read <= 0 or stats.indexed != stats.rows_read:
            raise GlobalMetricsIndexingError(
                f"Importação incompleta do arquivo de métricas globais {upload_file.pk} em {target_index}: "
                f"{stats.rows_read} linha(s) lida(s), {stats.indexed} indexada(s)."
            )

        upload_file.mark_processed()
    except (OperationalError, InterfaceError):
        if stats is not None:
            logging.exception(
                f"Arquivo de métricas globais {upload_file.pk} indexado em {target_index} "
                f"({stats.indexed} registros), mas falhou ao persistir status processado."
            )
        raise
    finally:
        close_old_connections()

    logging.info(
        f"Arquivo de métricas globais {upload_file.pk} indexado em "
        f"{target_index}: "
        f"{stats.rows_read} linhas lidas, {stats.indexed} indexadas, {stats.failed} falhas."
    )
    return {
        "rows_read": stats.rows_read,
        "indexed": stats.indexed,
        "failed": stats.failed,
        "errors": stats.errors,
    }
