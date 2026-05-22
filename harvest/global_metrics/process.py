import logging
from pathlib import Path

from django.conf import settings

from harvest.global_metrics.indexing import index_file_obj



def process_global_metrics_upload_file(upload_file_id, index_name=None, chunk_size=None):
    from harvest.models import GlobalMetricsUploadFile

    upload_file = GlobalMetricsUploadFile.objects.get(pk=upload_file_id)

    with upload_file.file.open("rb") as file_obj:
        stats = index_file_obj(
            file_obj=file_obj,
            file_name=Path(upload_file.file.name).name,
            index_name=index_name,
            chunk_size=chunk_size,
        )

    upload_file.mark_processed()
    logging.info(
        f"Arquivo de métricas globais {upload_file.pk} indexado em "
        f"{index_name or settings.GLOBAL_METRICS_FILE_UPLOAD_OPENSEARCH_INDEX}: "
        f"{stats.rows_read} linhas lidas, {stats.indexed} indexadas, {stats.failed} falhas."
    )
    return {
        "rows_read": stats.rows_read,
        "indexed": stats.indexed,
        "failed": stats.failed,
        "errors": stats.errors,
    }
