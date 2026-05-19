import csv
import hashlib
import importlib
import io
import json
import logging
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from opensearchpy.helpers import streaming_bulk
from slugify import slugify

from search_gateway.client import get_opensearch_client

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


class HarvestUploadIndexingError(Exception):
    """Raised when an uploaded harvest file cannot be indexed."""


class ImportStats:
    def __init__(self):
        self.rows_read = 0
        self.indexed = 0
        self.failed = 0
        self.errors = []


def _get_supported_extension(file_name):
    extension = Path(file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HarvestUploadIndexingError("Formato não suportado. Envie um arquivo .csv ou .xlsx.")
    return extension


def index_file_obj(file_obj, file_name, index_name=None, chunk_size=None):
    return index_prepared_rows(
        rows=iter_file_rows(file_obj=file_obj, file_name=file_name),
        file_name=file_name,
        extension=_get_supported_extension(file_name),
        index_name=index_name,
        chunk_size=chunk_size,
    )


def iter_file_rows(file_obj, file_name):
    extension = _get_supported_extension(file_name)
    yield from _iter_rows(file_obj=file_obj, extension=extension)


def index_prepared_rows(
    rows,
    file_name,
    extension,
    index_name=None,
    chunk_size=None,
):
    index_name = index_name or settings.HARVEST_UPLOAD_OPENSEARCH_INDEX
    chunk_size = chunk_size or settings.HARVEST_UPLOAD_BULK_CHUNK_SIZE
    extension = extension.lstrip(".")
    client = get_opensearch_client()
    if client is None:
        raise HarvestUploadIndexingError("Cliente OpenSearch não configurado.")

    stats = ImportStats()
    actions = _iter_bulk_actions(
        rows=rows,
        index_name=index_name,
        source_file=file_name,
        extension=extension,
        stats=stats,
    )

    for ok, result in streaming_bulk(
        client=client,
        actions=actions,
        chunk_size=chunk_size,
        raise_on_error=False,
        raise_on_exception=False,
    ):
        if ok:
            stats.indexed += 1
            continue

        stats.failed += 1
        _append_error(stats=stats, error=_format_bulk_error(result))

    return stats


def _iter_rows(file_obj, extension):
    file_obj.seek(0)
    if extension == ".csv":
        yield from _iter_csv_rows(file_obj)
        return
    if extension == ".xlsx":
        yield from _iter_xlsx_rows(file_obj)
        return


def _iter_csv_rows(file_obj):
    file_obj.seek(0)
    wrapper = io.TextIOWrapper(file_obj, encoding="utf-8-sig", newline="")

    reader = csv.reader(wrapper, delimiter=settings.DIRECTORY_IMPORT_DELIMITER)
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise HarvestUploadIndexingError("O arquivo CSV está vazio.") from exc

    yield from _iter_data_rows(headers=headers, rows=reader)


def _iter_xlsx_rows(file_obj):
    try:
        CalamineWorkbook = importlib.import_module("python_calamine").CalamineWorkbook
    except ImportError as exc:
        raise HarvestUploadIndexingError("A dependência python-calamine não está instalada.") from exc

    file_path = _get_file_path(file_obj)
    if not file_path:
        raise HarvestUploadIndexingError("python-calamine precisa de um arquivo local para ler XLSX.")

    try:
        workbook = CalamineWorkbook.from_path(file_path)
        worksheet = workbook.get_sheet_by_index(0)
        rows = worksheet.iter_rows() if hasattr(worksheet, "iter_rows") else iter(worksheet.to_python())
        headers = next(rows)
    except StopIteration as exc:
        raise HarvestUploadIndexingError("O arquivo XLSX está vazio.") from exc
    except Exception as exc:
        raise HarvestUploadIndexingError(f"Falha ao ler XLSX com python-calamine: {exc}") from exc

    yield from _iter_data_rows(headers=headers, rows=rows)


def _get_file_path(file_obj):
    for candidate in (
        getattr(file_obj, "path", None),
        getattr(getattr(file_obj, "file", None), "name", None),
        getattr(file_obj, "name", None),
    ):
        if candidate and Path(candidate).is_absolute():
            return candidate
    return None


def _iter_data_rows(headers, rows):
    normalized_headers = _normalize_headers(headers=headers)
    for row_number, row in enumerate(rows, start=2):
        if not any(_has_value(value) for value in row):
            continue
        yield row_number, _row_to_dict(headers=normalized_headers, row=row)


def _iter_bulk_actions(
    rows,
    index_name,
    source_file,
    extension,
    stats,
):
    for row_number, raw_data in rows:
        stats.rows_read += 1
        document_id = _build_document_id(raw_data)
        yield {
            "_op_type": "index",
            "_index": index_name,
            "_id": document_id,
            "_source": {
                "source_file": source_file,
                "source_format": extension,
                "row_number": row_number,
                "raw_data": raw_data,
            },
        }


def _normalize_headers(headers):
    headers = list(headers)
    if not any(_has_value(header) for header in headers):
        raise HarvestUploadIndexingError("O arquivo precisa conter uma linha de cabeçalho.")

    normalized_headers = []
    seen = {}
    for index, header in enumerate(headers, start=1):
        header_name = _serialize_value(header)
        header_name = str(header_name).strip() if header_name is not None else ""
        normalized = slugify(header_name, separator="_") or f"column_{index}"
        count = seen.get(normalized, 0) + 1
        seen[normalized] = count
        if count > 1:
            normalized = f"{normalized}_{count}"
        normalized_headers.append(normalized)

    return normalized_headers


def _row_to_dict(headers, row):
    values = list(row)
    document = {}
    for index, header in enumerate(headers):
        value = values[index] if index < len(values) else None
        value = _serialize_value(value)
        if value is not None:
            document[header] = value
    return document


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _build_document_id(raw_data):
    base_id = raw_data.get("baseid")
    year = raw_data.get("year")
    if base_id and year:
        return f"{base_id}-{year}"

    payload = json.dumps(raw_data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _format_bulk_error(result):
    try:
        action_result = next(iter(result.values()))
        document_id = action_result.get("_id")
        error = action_result.get("error")
        return f"{document_id}: {error}"
    except Exception:
        return str(result)


def _append_error(stats, error):
    logger.warning("Falha ao indexar linha de upload harvest: %s", error)
    if len(stats.errors) < 10:
        stats.errors.append(error)

