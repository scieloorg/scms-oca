"""
Observation views - duplicated from search (searchv2) to be self-contained.
No changes to the search application.
"""
import json
import logging
import traceback
import time
import uuid
import builtins
import threading
from copy import deepcopy
from io import StringIO
import csv

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from observation.models import ObservationPage
from search_gateway.filter_mapping import get_mapped_filters
from search_gateway.query import build_bool_query_from_search_params
from search_gateway.request_filters import (
    extract_applied_filters,
    normalize_option_filters,
)
from search_gateway.service import SearchGatewayService

logger = logging.getLogger(__name__)

OBSERVATION_SEARCH_FORM_KEY = "search"
OBSERVATION_YEAR_START = 2019
OBSERVATION_YEAR_END = 2025
EXPORT_JOBS = {}
EXPORT_JOBS_LOCK = threading.Lock()


def _get_index_name(request):
    return request.GET.get(
        "index_name",
        getattr(settings, "OP_INDEX_SCIENTIFIC_PRODUCTION", "scientific_production"),
    )


def _build_nested_terms_aggs(*, row_field, col_field, row_size, col_size):
    return {
        "by_row": {
            "terms": {"field": row_field, "size": row_size},
            "aggs": {
                "by_col": {
                    "terms": {"field": col_field, "size": col_size},
                },
            },
        },
    }


def _expand_agg_field_candidates(candidates):
    expanded = []
    for candidate in candidates:
        cleaned = str(candidate or "").strip()
        if not cleaned:
            continue
        variants = [cleaned]
        if not cleaned.endswith(".keyword"):
            variants.append(f"{cleaned}.keyword")
        for variant in variants:
            if variant not in expanded:
                expanded.append(variant)
    return expanded


def _is_text_fielddata_error(exc):
    message = str(exc or "")
    return (
        "Text fields are not optimised" in message
        and "fielddata=true" in message
    )


def _resolve_observation_dimension(request):
    page_id = request.GET.get("page_id")
    dimension_slug = request.GET.get("dimension_slug")
    if not page_id:
        return None
    try:
        page = ObservationPage.objects.get(id=int(page_id))
    except (ObservationPage.DoesNotExist, TypeError, ValueError):
        return None
    if dimension_slug:
        for item in page.get_dimensions_config():
            if item.get("slug") == dimension_slug:
                return item
    return page.get_default_dimension_config()


def _parse_query_clauses_from_source(source):
    raw = source.get("search_clauses")
    if not raw:
        return []
    try:
        clauses = json.loads(raw)
        return clauses if isinstance(clauses, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _normalize_field_name_variant(value):
    cleaned = str(value or "").strip()
    if cleaned.endswith(".keyword"):
        return cleaned[: -len(".keyword")]
    return cleaned


def _resolve_lookup_field_name(service, row_field_name, row_index_field=None):
    data_source = service.data_source
    if not data_source:
        return None

    preferred_field = data_source.get_field(row_field_name) if row_field_name else None
    if preferred_field and preferred_field.lookup:
        return row_field_name

    candidates = {
        _normalize_field_name_variant(row_field_name),
        _normalize_field_name_variant(row_index_field),
    }
    candidates.discard("")

    field_settings = data_source.field_settings_dict or {}
    for field_name, cfg in field_settings.items():
        if not cfg.get("lookup"):
            continue
        normalized_field_name = _normalize_field_name_variant(field_name)
        normalized_index_name = _normalize_field_name_variant(cfg.get("index_field_name"))
        if (
            normalized_field_name in candidates
            or normalized_index_name in candidates
        ):
            return field_name
    return None


def _apply_lookup_labels_to_rows(service, row_field_name, result, row_index_field=None):
    if not result or not row_field_name:
        return result

    lookup_field_name = _resolve_lookup_field_name(
        service,
        row_field_name=row_field_name,
        row_index_field=row_index_field,
    )
    if not lookup_field_name:
        return result

    rows = result.get("rows") or []
    row_keys = [
        str(row.get("key")).strip()
        for row in rows
        if row.get("key") not in (None, "")
    ]
    if not row_keys:
        return result

    lookup_options = []
    lookup_error = None
    batch_size = 200
    for start in range(0, len(row_keys), batch_size):
        batch = row_keys[start : start + batch_size]
        batch_options, batch_error = service.get_lookup_options_by_values(
            lookup_field_name,
            batch,
        )
        if batch_error:
            lookup_error = batch_error
            break
        lookup_options.extend(batch_options or [])
    if lookup_error or not lookup_options:
        logger.warning(
            "Observation table: lookup label resolution failed for field %s (lookup=%s): %s",
            row_field_name,
            lookup_field_name,
            lookup_error or "empty lookup response",
        )
        return result

    label_by_value = {
        str(option.get("value", "")).strip(): option.get("label")
        for option in lookup_options
        if str(option.get("value", "")).strip()
    }
    if not label_by_value:
        return result

    for row in rows:
        key = str(row.get("key", "")).strip()
        if not key:
            continue
        resolved_label = label_by_value.get(key)
        if resolved_label:
            row["label"] = resolved_label

    return result


def _resolve_lookup_labels_for_export_rows(service, row_field_name, rows, row_index_field=None):
    if not rows:
        return rows
    wrapped = {"rows": rows}
    resolved = _apply_lookup_labels_to_rows(
        service,
        row_field_name,
        wrapped,
        row_index_field=row_index_field,
    )
    return resolved.get("rows") or rows


def _observation_year_columns():
    return [str(year) for year in range(OBSERVATION_YEAR_START, OBSERVATION_YEAR_END + 1)]


def _normalize_year_columns_result(result):
    normalized = dict(result or {})
    year_columns = _observation_year_columns()
    normalized["columns"] = year_columns

    rows = normalized.get("rows") or []
    for row in rows:
        values = row.get("values") or {}
        row["values"] = {
            year: int(values.get(year, 0) or 0)
            for year in year_columns
        }
    return normalized


def _estimate_dimension_row_total(
    service,
    *,
    query_text,
    query_clauses,
    selected_filters,
    row_field,
):
    if not row_field:
        return 0
    try:
        mapped_filters = get_mapped_filters(selected_filters or {}, service.field_settings)
        bool_query = build_bool_query_from_search_params(
            query_text=query_text if not query_clauses else None,
            query_clauses=query_clauses if query_clauses else None,
            filters=mapped_filters,
        )
        response = service.client.search(
            index=service.index_name,
            body={
                "size": 0,
                "query": {"bool": bool_query},
                "aggs": {
                    "row_total": {
                        "cardinality": {
                            "field": row_field,
                            "precision_threshold": 40000,
                        }
                    }
                },
            },
            request_cache=True,
            request_timeout=service.request_timeout,
        )
        return int(
            (((response.get("aggregations") or {}).get("row_total") or {}).get("value"))
            or 0
        )
    except Exception:
        logger.exception("Observation table: failed to estimate row_total for field %s", row_field)
        return 0


def _build_dimension_table_result(query_source, service, dimension):
    applied_filters = extract_applied_filters(
        query_source,
        service.data_source,
        form_key=OBSERVATION_SEARCH_FORM_KEY,
    )
    selected_filters = normalize_option_filters(applied_filters)
    text_search = query_source.get("search", "")
    query_clauses = _parse_query_clauses_from_source(query_source)
    field_settings = service.data_source.field_settings_dict or {}

    row_field_name = dimension.get("row_field_name") or "country"
    col_field_name = dimension.get("col_field_name") or "publication_year"
    row_cfg = field_settings.get(row_field_name, {})
    col_cfg = field_settings.get(col_field_name, {})
    row_field = row_cfg.get("index_field_name")
    col_field = col_cfg.get("index_field_name")

    row_size = int(
        dimension.get("row_bucket_size")
        or row_cfg.get("filter", {}).get("size", 500)
    )
    col_size = int(
        dimension.get("col_bucket_size")
        or col_cfg.get("filter", {}).get("size", 300)
    )
    parse_config = {
        "row_agg_name": "by_row",
        "col_agg_name": "by_col",
        "row_field_name": row_field_name,
    }
    row_transform = row_cfg.get("settings", {}).get("display_transform")
    if row_transform:
        parse_config["row_display_transform"] = row_transform
    def _run_aggregation(row_index_field, col_index_field):
        if not row_index_field or not col_index_field:
            return {"columns": [], "rows": [], "grand_total": 0}
        aggs = _build_nested_terms_aggs(
            row_field=row_index_field,
            col_field=col_index_field,
            row_size=row_size,
            col_size=col_size,
        )
        return service.search_aggregation(
            aggs=aggs,
            query_text=text_search if not query_clauses else None,
            query_clauses=query_clauses if query_clauses else None,
            filters=selected_filters,
            parse_config=parse_config,
        )

    row_candidates = _expand_agg_field_candidates(
        [row_field, row_field_name, "author_country_codes", "country"]
    )
    col_candidates = _expand_agg_field_candidates(
        [col_field, col_field_name, "publication_year"]
    )

    result = {"columns": [], "rows": [], "grand_total": 0}
    used_pair = None
    for row_candidate in row_candidates:
        for col_candidate in col_candidates:
            try:
                candidate_result = _run_aggregation(row_candidate, col_candidate)
            except Exception as exc:
                if _is_text_fielddata_error(exc):
                    logger.info(
                        "Skipping aggregation candidate pair row=%s col=%s due to text fielddata restriction",
                        row_candidate,
                        col_candidate,
                    )
                    continue
                raise
            if (candidate_result.get("rows") or []):
                result = candidate_result
                used_pair = (row_candidate, col_candidate)
                break
            if not result.get("rows"):
                result = candidate_result
        if used_pair:
            break
    if used_pair and (used_pair[0] != row_field or used_pair[1] != col_field):
        logger.info(
            "Observation export/table fallback fields in use: row=%s col=%s (configured row=%s col=%s)",
            used_pair[0],
            used_pair[1],
            row_field,
            col_field,
        )
    result["row_total"] = _estimate_dimension_row_total(
        service,
        query_text=text_search,
        query_clauses=query_clauses,
        selected_filters=selected_filters,
        row_field=(used_pair[0] if used_pair else row_field),
    )
    labeled_result = _apply_lookup_labels_to_rows(
        service,
        row_field_name,
        result,
        row_index_field=(used_pair[0] if used_pair else row_field),
    )
    return _normalize_year_columns_result(labeled_result)


def _build_dimension_table_result_all_rows(
    query_source,
    service,
    dimension,
    split_size=1000,
    progress_callback=None,
):
    """
    Build the same row/column structure used by the table, but paginating all row buckets
    with composite aggregation so exports are not capped by terms size.
    """
    applied_filters = extract_applied_filters(
        query_source,
        service.data_source,
        form_key=OBSERVATION_SEARCH_FORM_KEY,
    )
    selected_filters = normalize_option_filters(applied_filters)
    text_search = query_source.get("search", "")
    query_clauses = _parse_query_clauses_from_source(query_source)
    field_settings = service.data_source.field_settings_dict or {}

    row_field_name = dimension.get("row_field_name") or "country"
    col_field_name = dimension.get("col_field_name") or "publication_year"
    row_cfg = field_settings.get(row_field_name, {})
    col_cfg = field_settings.get(col_field_name, {})
    configured_row_field = row_cfg.get("index_field_name")
    configured_col_field = col_cfg.get("index_field_name")
    col_size = int(
        dimension.get("col_bucket_size")
        or col_cfg.get("filter", {}).get("size", 300)
    )

    mapped_filters = get_mapped_filters(selected_filters or {}, service.field_settings)
    bool_query = build_bool_query_from_search_params(
        query_text=text_search if not query_clauses else None,
        query_clauses=query_clauses if query_clauses else None,
        filters=mapped_filters,
    )

    row_transform = row_cfg.get("settings", {}).get("display_transform")

    def _col_sort_key(key):
        try:
            return (0, int(key))
        except (TypeError, ValueError):
            return (1, str(key))

    row_candidates = _expand_agg_field_candidates(
        [configured_row_field, row_field_name, "author_country_codes", "country"]
    )
    col_candidates = _expand_agg_field_candidates(
        [configured_col_field, col_field_name, "publication_year"]
    )

    page_size = max(100, int(split_size or 1000))
    best_result = {"columns": [], "rows": [], "grand_total": 0}
    used_pair = None
    processed_rows = 0

    for row_field in row_candidates:
        for col_field in col_candidates:
            after_key = None
            rows = []
            col_keys = set()
            grand_total = 0
            try:
                while True:
                    composite = {
                        "size": page_size,
                        "sources": [{"row_key": {"terms": {"field": row_field}}}],
                    }
                    if after_key:
                        composite["after"] = after_key
                    aggs = {
                        "by_row": {
                            "composite": composite,
                            "aggs": {
                                "by_col": {"terms": {"field": col_field, "size": col_size}},
                            },
                        }
                    }
                    body = {
                        "size": 0,
                        "track_total_hits": True,
                        "query": {"bool": bool_query},
                        "aggs": aggs,
                    }
                    response = service.client.search(
                        index=service.index_name,
                        body=body,
                        request_cache=True,
                        request_timeout=service.request_timeout,
                    )
                    row_agg = (response.get("aggregations") or {}).get("by_row") or {}
                    buckets = row_agg.get("buckets") or []
                    if not buckets:
                        break
                    for rb in buckets:
                        raw_key = ((rb.get("key") or {}).get("row_key"))
                        if row_transform:
                            label = raw_key
                        else:
                            label = raw_key
                        values = {}
                        for cb in (rb.get("by_col") or {}).get("buckets", []) or []:
                            ck = cb.get("key")
                            if ck is None:
                                continue
                            values[str(ck)] = cb.get("doc_count", 0)
                            col_keys.add(ck)
                        rows.append({"key": raw_key, "label": label, "values": values})
                        grand_total += int(rb.get("doc_count") or 0)
                        processed_rows += 1
                    if callable(progress_callback):
                        progress_callback(processed_rows)
                    after_key = row_agg.get("after_key")
                    if not after_key:
                        break
            except Exception as exc:
                if _is_text_fielddata_error(exc):
                    logger.info(
                        "Skipping composite aggregation candidate pair row=%s col=%s due to text fielddata restriction",
                        row_field,
                        col_field,
                    )
                    continue
                raise

            columns = [str(c) for c in sorted(col_keys, key=_col_sort_key)]
            candidate_result = {"columns": columns, "rows": rows, "grand_total": grand_total}
            if rows:
                used_pair = (row_field, col_field)
                best_result = candidate_result
                break
            if not best_result.get("rows"):
                best_result = candidate_result
        if used_pair:
            break

    if used_pair and (used_pair[0] != configured_row_field or used_pair[1] != configured_col_field):
        logger.info(
            "Observation export(all rows) fallback fields in use: row=%s col=%s (configured row=%s col=%s)",
            used_pair[0],
            used_pair[1],
            configured_row_field,
            configured_col_field,
        )
    labeled_result = _apply_lookup_labels_to_rows(
        service,
        row_field_name,
        best_result,
        row_index_field=(used_pair[0] if used_pair else configured_row_field),
    )
    return _normalize_year_columns_result(labeled_result)


def _job_snapshot(job):
    snapshot = {
        "id": job["id"],
        "job_type": job.get("job_type", "file"),
        "parent_id": job.get("parent_id"),
        "sequence": job.get("sequence"),
        "range_start": job.get("range_start"),
        "range_end": job.get("range_end"),
        "status": job["status"],
        "message": job.get("message", ""),
        "progress_percent": job.get("progress_percent", 0),
        "processed_rows": job.get("processed_rows", 0),
        "total_rows": job.get("total_rows", 0),
        "file_name": job.get("file_name", ""),
        "dimension_slug": job.get("dimension_slug", ""),
        "dimension_label": job.get("dimension_label", ""),
        "created_at": job.get("created_at"),
        "finished_at": job.get("finished_at"),
    }
    if job.get("status") == "error" and job.get("debug"):
        snapshot["debug"] = job.get("debug")
    if job.get("job_type") == "batch":
        snapshot["ready_files_count"] = len(job.get("ready_file_ids") or [])
    return snapshot


def _run_export_job(
    job_id,
    *,
    query_string,
    index_name,
    dimension,
    batch_size,
    progress_step,
    export_scope="current",
    split_size=1000,
):
    stage = "initializing"
    job = EXPORT_JOBS.get(job_id)
    if not job:
        return
    job["status"] = "running"
    job["message"] = _("Preparing CSV data...")
    EXPORT_JOBS[job_id] = job

    try:
        from django.http import QueryDict

        stage = "parse_querystring"
        request_get = QueryDict(query_string, mutable=False)
        stage = "build_service"
        service = SearchGatewayService(index_name=index_name)
        if not service.data_source:
            raise ValueError("Invalid data source for export")

        stage = "build_table_result"
        scope_is_all = str(export_scope or "current").strip().lower() == "all"
        discovery_pages = {"count": 0}

        def _update_discovery_progress(discovered_rows):
            if not scope_is_all:
                return
            if discovered_rows <= 0:
                return
            discovery_pages["count"] += 1
            # Keep discovery phase under 70%, then writing phase fills to 100%.
            discovery_progress = min(70, 5 + (discovery_pages["count"] * 2))
            current = EXPORT_JOBS.get(job_id)
            if not current:
                return
            current["processed_rows"] = int(discovered_rows)
            current["total_rows"] = max(int(discovered_rows), int(current.get("total_rows") or 0))
            current["progress_percent"] = max(int(current.get("progress_percent") or 0), discovery_progress)
            current["message"] = _("Collecting rows for single CSV... %(rows)s") % {
                "rows": discovered_rows,
            }
            EXPORT_JOBS[job_id] = current

        if str(export_scope or "current").strip().lower() == "all":
            result = _build_dimension_table_result_all_rows(
                request_get,
                service,
                dimension,
                split_size=split_size,
                progress_callback=_update_discovery_progress,
            )
        else:
            result = _build_dimension_table_result(request_get, service, dimension)
        stage = "extract_rows"
        columns = tuple(result.get("columns") or [])
        rows = tuple(result.get("rows") or [])
        total_rows = len(rows)

        job = EXPORT_JOBS[job_id]
        job["total_rows"] = total_rows
        job["processed_rows"] = 0
        job["progress_percent"] = 0
        job["message"] = _("Formatting CSV...")
        EXPORT_JOBS[job_id] = job

        stage = "prepare_csv"
        output = StringIO()
        writer = csv.writer(output)
        row_label = dimension.get("row_label") or _("Row")
        if columns:
            writer.writerow([row_label] + builtins.list(columns))
        else:
            writer.writerow([row_label, _("Message")])
            if total_rows == 0:
                writer.writerow(["-", _("No data returned for selected dimension and filters")])

        stage = "write_csv_rows"
        processed = 0
        step = max(1, int(progress_step or 100))
        chunk_size = max(1, int(batch_size or 1000))
        for chunk_start in range(0, total_rows, chunk_size):
            chunk = rows[chunk_start:chunk_start + chunk_size]
            for row in chunk:
                values = row.get("values") or {}
                writer.writerow(
                    [row.get("label") or row.get("key") or ""]
                    + [values.get(col, 0) for col in columns]
                )
                processed += 1
                if processed % step == 0 or processed == total_rows:
                    current = EXPORT_JOBS[job_id]
                    current["processed_rows"] = processed
                    if scope_is_all:
                        current["progress_percent"] = 70 + int((processed * 30) / max(total_rows, 1))
                    else:
                        current["progress_percent"] = int((processed * 100) / max(total_rows, 1))
                    current["message"] = _("Generating CSV... %(processed)s/%(total)s") % {
                        "processed": processed,
                        "total": total_rows,
                    }
                    EXPORT_JOBS[job_id] = current
            time.sleep(0.01)

        stage = "finalize_job"
        done = EXPORT_JOBS[job_id]
        done["status"] = "done"
        done["csv_content"] = output.getvalue()
        done["processed_rows"] = total_rows
        done["progress_percent"] = 100
        done["message"] = _("CSV ready (%(rows)s rows)") % {"rows": total_rows}
        done["finished_at"] = int(time.time())
        EXPORT_JOBS[job_id] = done
    except Exception as exc:
        logger.exception("Observation export failed: %s", exc)
        failed = EXPORT_JOBS.get(job_id)
        if not failed:
            return
        failed["status"] = "error"
        failed["message"] = f"{type(exc).__name__} at {stage}: {exc}"
        failed["debug"] = traceback.format_exc(limit=6)
        failed["finished_at"] = int(time.time())
        EXPORT_JOBS[job_id] = failed


def _store_done_csv_job(
    *,
    dimension,
    file_name,
    csv_content,
    total_rows,
    parent_id=None,
    sequence=None,
    range_start=None,
    range_end=None,
):
    job_id = str(uuid.uuid4())
    slug = dimension.get("slug") or ""
    label = dimension.get("menu_label") or slug or _("Dimension")
    safe_csv_content = csv_content
    if not isinstance(safe_csv_content, str) or not safe_csv_content.strip():
        fallback = StringIO()
        fallback_writer = csv.writer(fallback)
        fallback_writer.writerow([_("Message")])
        fallback_writer.writerow([_("No data available for export")])
        safe_csv_content = fallback.getvalue()
    with EXPORT_JOBS_LOCK:
        EXPORT_JOBS[job_id] = {
        "id": job_id,
        "job_type": "file",
        "parent_id": parent_id,
        "sequence": sequence,
        "range_start": range_start,
        "range_end": range_end,
        "status": "done",
        "message": _("CSV ready (%(rows)s rows)") % {"rows": total_rows},
        "progress_percent": 100,
        "processed_rows": total_rows,
        "total_rows": total_rows,
        "file_name": file_name,
        "dimension_slug": slug,
        "dimension_label": label,
        "created_at": int(time.time()),
        "finished_at": int(time.time()),
        "csv_content": safe_csv_content,
        }
        return _job_snapshot(EXPORT_JOBS[job_id])


def _store_pending_csv_job(*, dimension, file_name, message):
    job_id = str(uuid.uuid4())
    slug = dimension.get("slug") or ""
    label = dimension.get("menu_label") or slug or _("Dimension")
    with EXPORT_JOBS_LOCK:
        EXPORT_JOBS[job_id] = {
            "id": job_id,
            "job_type": "file",
            "status": "queued",
            "message": message,
            "progress_percent": 0,
            "processed_rows": 0,
            "total_rows": 0,
            "file_name": file_name,
            "dimension_slug": slug,
            "dimension_label": label,
            "created_at": int(time.time()),
            "finished_at": None,
            "csv_content": "",
        }
        return _job_snapshot(EXPORT_JOBS[job_id])


def _store_error_job(*, dimension, message, debug=""):
    job_id = str(uuid.uuid4())
    slug = dimension.get("slug") or ""
    label = dimension.get("menu_label") or slug or _("Dimension")
    with EXPORT_JOBS_LOCK:
        EXPORT_JOBS[job_id] = {
        "id": job_id,
        "job_type": "file",
        "status": "error",
        "message": message,
        "progress_percent": 0,
        "processed_rows": 0,
        "total_rows": 0,
        "file_name": "",
        "dimension_slug": slug,
        "dimension_label": label,
        "created_at": int(time.time()),
        "finished_at": int(time.time()),
        "csv_content": "",
        "debug": debug or "",
        }
        return _job_snapshot(EXPORT_JOBS[job_id])


def _store_batch_job(*, dimension, message):
    job_id = str(uuid.uuid4())
    slug = dimension.get("slug") or ""
    label = dimension.get("menu_label") or slug or _("Dimension")
    with EXPORT_JOBS_LOCK:
        EXPORT_JOBS[job_id] = {
            "id": job_id,
            "job_type": "batch",
            "status": "running",
            "message": message,
            "progress_percent": 0,
            "processed_rows": 0,
            "total_rows": 0,
            "file_name": "",
            "dimension_slug": slug,
            "dimension_label": label,
            "created_at": int(time.time()),
            "finished_at": None,
            "csv_content": "",
            "ready_file_ids": [],
        }
        return _job_snapshot(EXPORT_JOBS[job_id])


def _build_csv_content(*, dimension, columns, rows):
    output = StringIO()
    writer = csv.writer(output)
    row_label = dimension.get("row_label") or _("Row")
    if columns:
        writer.writerow([row_label] + builtins.list(columns))
        for row in rows:
            values = row.get("values") or {}
            writer.writerow(
                [row.get("label") or row.get("key") or ""]
                + [values.get(col, 0) for col in columns]
            )
    elif rows:
        writer.writerow([row_label, _("Total")])
        for row in rows:
            values = row.get("values") or {}
            total = 0
            for value in values.values():
                try:
                    total += int(value or 0)
                except (TypeError, ValueError):
                    continue
            writer.writerow([row.get("label") or row.get("key") or "", total])
    else:
        writer.writerow([row_label, _("Message")])
        writer.writerow(["-", _("No data returned for selected dimension and filters")])
    return output.getvalue()


def _normalize_csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def _build_documents_csv_content(rows):
    output = StringIO()
    writer = csv.writer(output)
    if not rows:
        writer.writerow([_("Message")])
        writer.writerow([_("No documents returned for selected dimension and filters")])
        return output.getvalue()

    header_keys = []
    seen = set()
    for source in rows:
        for key in source.keys():
            if key not in seen:
                seen.add(key)
                header_keys.append(str(key))

    writer.writerow(header_keys)
    for source in rows:
        writer.writerow([_normalize_csv_value(source.get(key)) for key in header_keys])
    return output.getvalue()


def _build_document_export_jobs(*, dimension, query_source, index_name, split_size):
    service = SearchGatewayService(index_name=index_name)
    data_source = service.data_source
    if not data_source:
        return []

    query_clauses = _parse_query_clauses_from_source(query_source)
    text_search = query_source.get("search", "")
    applied_filters = extract_applied_filters(
        query_source,
        data_source,
        form_key=OBSERVATION_SEARCH_FORM_KEY,
    )
    selected_filters = normalize_option_filters(applied_filters)

    jobs = []
    file_slug = (dimension.get("slug") or "dimension").strip() or "dimension"
    mapped_filters = get_mapped_filters(selected_filters or {}, service.field_settings)
    bool_query = build_bool_query_from_search_params(
        query_text=text_search if not query_clauses else None,
        query_clauses=query_clauses if query_clauses else None,
        filters=mapped_filters,
    )
    search_body = {
        "size": split_size,
        "query": {"bool": bool_query},
        "sort": ["_doc"],
    }
    if service.source_fields:
        search_body["_source"] = service.source_fields

    scroll_id = None
    part_idx = 1
    try:
        response = service.client.search(
            index=service.index_name,
            body=search_body,
            scroll="2m",
            request_timeout=service.request_timeout,
        )
        scroll_id = response.get("_scroll_id")
        while True:
            hits = ((response.get("hits") or {}).get("hits") or [])
            if not hits:
                break
            sources = [hit.get("_source") or {} for hit in hits]
            csv_content = _build_documents_csv_content(sources)
            file_name = f"observation_{file_slug}_{int(time.time())}_part_{part_idx:03d}.csv"
            jobs.append(
                _store_done_csv_job(
                    dimension=dimension,
                    file_name=file_name,
                    csv_content=csv_content,
                    total_rows=len(sources),
                    sequence=part_idx,
                    range_start=((part_idx - 1) * split_size) + 1,
                    range_end=((part_idx - 1) * split_size) + len(sources),
                )
            )
            part_idx += 1
            if not scroll_id:
                break
            response = service.client.scroll(
                scroll_id=scroll_id,
                scroll="2m",
                request_timeout=service.request_timeout,
            )
            scroll_id = response.get("_scroll_id") or scroll_id
    finally:
        if scroll_id:
            try:
                service.client.clear_scroll(scroll_id=scroll_id)
            except Exception:
                logger.warning("Failed to clear OpenSearch scroll context", exc_info=True)
    return jobs


def _run_chunked_export_async(*, batch_job_id, dimension, query_source, index_name, split_size):
    try:
        service = SearchGatewayService(index_name=index_name)
        data_source = service.data_source
        if not data_source:
            raise ValueError("Invalid data source for export")

        applied_filters = extract_applied_filters(
            query_source,
            data_source,
            form_key=OBSERVATION_SEARCH_FORM_KEY,
        )
        selected_filters = normalize_option_filters(applied_filters)
        query_clauses = _parse_query_clauses_from_source(query_source)
        text_search = query_source.get("search", "")
        mapped_filters = get_mapped_filters(selected_filters or {}, service.field_settings)
        bool_query = build_bool_query_from_search_params(
            query_text=text_search if not query_clauses else None,
            query_clauses=query_clauses if query_clauses else None,
            filters=mapped_filters,
        )

        field_settings = data_source.field_settings_dict or {}
        row_field_name = dimension.get("row_field_name") or "country"
        col_field_name = dimension.get("col_field_name") or "publication_year"
        row_cfg = field_settings.get(row_field_name, {})
        col_cfg = field_settings.get(col_field_name, {})
        configured_row_field = row_cfg.get("index_field_name")
        configured_col_field = col_cfg.get("index_field_name")
        col_size = int(
            dimension.get("col_bucket_size")
            or col_cfg.get("filter", {}).get("size", 300)
        )

        row_candidates = []
        for candidate in [configured_row_field, row_field_name, "author_country_codes", "country"]:
            cleaned = str(candidate or "").strip()
            if cleaned and cleaned not in row_candidates:
                row_candidates.append(cleaned)
        col_candidates = []
        for candidate in [configured_col_field, col_field_name, "publication_year"]:
            cleaned = str(candidate or "").strip()
            if cleaned and cleaned not in col_candidates:
                col_candidates.append(cleaned)

        def _estimate_total_rows(row_field):
            body = {
                "size": 0,
                "query": {"bool": bool_query},
                "aggs": {"row_count": {"cardinality": {"field": row_field}}},
            }
            response = service.client.search(
                index=service.index_name,
                body=body,
                request_cache=True,
                request_timeout=service.request_timeout,
            )
            return int((((response.get("aggregations") or {}).get("row_count") or {}).get("value")) or 0)

        split_size = max(1, int(split_size or 1000))
        page_size = max(100, min(split_size, 1000))
        processed_rows = 0
        part_idx = 1
        file_slug = (dimension.get("slug") or "dimension").strip() or "dimension"
        used_pair = None
        buffer_rows = []
        columns = []
        estimated_total = 0

        for row_field in row_candidates:
            for col_field in col_candidates:
                columns = _observation_year_columns()
                estimated_total = _estimate_total_rows(row_field)
                after_key = None
                found_any = False
                while True:
                    composite = {
                        "size": page_size,
                        "sources": [{"row_key": {"terms": {"field": row_field}}}],
                    }
                    if after_key:
                        composite["after"] = after_key
                    body = {
                        "size": 0,
                        "query": {"bool": bool_query},
                        "aggs": {
                            "by_row": {
                                "composite": composite,
                                "aggs": {
                                    "by_col": {"terms": {"field": col_field, "size": col_size}},
                                },
                            }
                        },
                    }
                    response = service.client.search(
                        index=service.index_name,
                        body=body,
                        request_cache=True,
                        request_timeout=service.request_timeout,
                    )
                    row_agg = (response.get("aggregations") or {}).get("by_row") or {}
                    buckets = row_agg.get("buckets") or []
                    if not buckets:
                        break
                    found_any = True
                    for rb in buckets:
                        raw_key = ((rb.get("key") or {}).get("row_key"))
                        values = {}
                        for cb in (rb.get("by_col") or {}).get("buckets", []) or []:
                            ck = cb.get("key")
                            if ck is None:
                                continue
                            values[str(ck)] = cb.get("doc_count", 0)
                        buffer_rows.append({"key": raw_key, "label": raw_key, "values": values})
                        if len(buffer_rows) >= split_size:
                            chunk_rows = builtins.list(buffer_rows[:split_size])
                            del buffer_rows[:split_size]
                            chunk_rows = _resolve_lookup_labels_for_export_rows(
                                service,
                                row_field_name,
                                chunk_rows,
                                row_index_field=row_field,
                            )
                            range_start = processed_rows + 1
                            processed_rows += len(chunk_rows)
                            range_end = processed_rows
                            csv_content = _build_csv_content(
                                dimension=dimension,
                                columns=columns,
                                rows=chunk_rows,
                            )
                            file_name = f"observation_{file_slug}_{int(time.time())}_part_{part_idx:03d}.csv"
                            child_snapshot = _store_done_csv_job(
                                dimension=dimension,
                                file_name=file_name,
                                csv_content=csv_content,
                                total_rows=len(chunk_rows),
                                parent_id=batch_job_id,
                                sequence=part_idx,
                                range_start=range_start,
                                range_end=range_end,
                            )
                            with EXPORT_JOBS_LOCK:
                                batch = EXPORT_JOBS.get(batch_job_id)
                                if not batch:
                                    break
                                ready_ids = batch.get("ready_file_ids") or []
                                ready_ids.append(child_snapshot["id"])
                                batch["ready_file_ids"] = ready_ids
                                batch["processed_rows"] = processed_rows
                                batch["total_rows"] = estimated_total
                                if estimated_total > 0:
                                    batch["progress_percent"] = min(99, int((processed_rows * 100) / estimated_total))
                                batch["message"] = _("Generating CSV files... %(processed)s/%(total)s") % {
                                    "processed": processed_rows,
                                    "total": estimated_total or processed_rows,
                                }
                                EXPORT_JOBS[batch_job_id] = batch
                            part_idx += 1
                    after_key = row_agg.get("after_key")
                    if not after_key:
                        break
                if found_any:
                    used_pair = (row_field, col_field)
                    break
                buffer_rows = []
                processed_rows = 0
                part_idx = 1
            if used_pair:
                break

        if not used_pair or (processed_rows == 0 and not buffer_rows):
            raise ValueError("No rows returned by backend for selected dimension and filters")

        if buffer_rows:
            chunk_rows = builtins.list(buffer_rows)
            chunk_rows = _resolve_lookup_labels_for_export_rows(
                service,
                row_field_name,
                chunk_rows,
                row_index_field=(used_pair[0] if used_pair else configured_row_field),
            )
            range_start = processed_rows + 1
            processed_rows += len(chunk_rows)
            range_end = processed_rows
            csv_content = _build_csv_content(
                dimension=dimension,
                columns=columns,
                rows=chunk_rows,
            )
            file_name = f"observation_{file_slug}_{int(time.time())}_part_{part_idx:03d}.csv"
            child_snapshot = _store_done_csv_job(
                dimension=dimension,
                file_name=file_name,
                csv_content=csv_content,
                total_rows=len(chunk_rows),
                parent_id=batch_job_id,
                sequence=part_idx,
                range_start=range_start,
                range_end=range_end,
            )
            with EXPORT_JOBS_LOCK:
                batch = EXPORT_JOBS.get(batch_job_id)
                if batch:
                    ready_ids = batch.get("ready_file_ids") or []
                    ready_ids.append(child_snapshot["id"])
                    batch["ready_file_ids"] = ready_ids
                    EXPORT_JOBS[batch_job_id] = batch

        with EXPORT_JOBS_LOCK:
            batch = EXPORT_JOBS.get(batch_job_id)
            if batch:
                batch["status"] = "done"
                batch["progress_percent"] = 100
                batch["finished_at"] = int(time.time())
                batch["message"] = _("All CSV files are ready")
                batch["total_rows"] = max(estimated_total, processed_rows)
                batch["processed_rows"] = processed_rows
                EXPORT_JOBS[batch_job_id] = batch
    except Exception as exc:
        logger.exception("Async chunked export failed: %s", exc)
        with EXPORT_JOBS_LOCK:
            batch = EXPORT_JOBS.get(batch_job_id)
            if batch:
                batch["status"] = "error"
                batch["finished_at"] = int(time.time())
                batch["message"] = f"{type(exc).__name__}: {exc}"
                batch["debug"] = traceback.format_exc(limit=6)
                EXPORT_JOBS[batch_job_id] = batch

@require_GET
def list(request):
    index_name = _get_index_name(request)
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("limit", 25))
    text_search = request.GET.get("search", "")
    query_clauses = _parse_query_clauses_from_source(request.GET)

    try:
        service = SearchGatewayService(index_name=index_name)
        data_source = service.data_source
        if not data_source:
            return JsonResponse({"error": "Invalid index_name"}, status=400)
        applied_filters = extract_applied_filters(
            request.GET, data_source, form_key=OBSERVATION_SEARCH_FORM_KEY
        )
        selected_filters = normalize_option_filters(applied_filters)
        results_data = service.search_documents(
            query_text=text_search if not query_clauses else None,
            query_clauses=query_clauses,
            filters=selected_filters,
            page=page,
            page_size=page_size,
            sort_field="publication_year",
            sort_order="desc",
        )
        return JsonResponse({
            "total_results": results_data.get("total_results", 0),
            "selected_filters": selected_filters,
        })
    except Exception as e:
        logger.exception("Error in observation api_search_results_list: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def filters(request):
    index_name = _get_index_name(request)

    try:
        service = SearchGatewayService(index_name=index_name)
        data_source = service.data_source
        if not data_source:
            return JsonResponse({"error": "Invalid index_name"}, status=400)
        filters, filters_error = service.get_filters_data()
        if filters_error:
            return JsonResponse({"error": filters_error}, status=500)
        form_key = OBSERVATION_SEARCH_FORM_KEY
        filter_metadata = data_source.get_filter_metadata(
            filters, form_key=form_key
        )
        return JsonResponse({
            "filters": filters,
            "filter_metadata": filter_metadata,
        })
    except Exception as e:
        logger.exception("Error in observation api_get_filters: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def table(request):
    index_name = _get_index_name(request)

    try:
        service = SearchGatewayService(index_name=index_name)
        if not service.data_source:
            return JsonResponse({"columns": [], "rows": [], "grand_total": 0})
        dimension = _resolve_observation_dimension(request) or {
            "row_field_name": "country",
            "col_field_name": "publication_year",
            "row_bucket_size": 500,
            "col_bucket_size": 300,
        }
        result = _build_dimension_table_result(request.GET, service, dimension)
        return JsonResponse(result)
    except Exception as e:
        logger.exception("Error in observation api_country_year_table: %s", e)
        return JsonResponse(
            {"error": str(e), "columns": [], "rows": [], "grand_total": 0},
            status=500,
        )


@require_GET
def export_start(request):
    index_name = _get_index_name(request)
    page_id = request.GET.get("page_id")
    scope = (request.GET.get("export_scope") or request.GET.get("scope") or "current").strip().lower()
    batch_size = int(request.GET.get("batch_size", 1000))
    progress_step = int(request.GET.get("progress_step", 100))
    row_bucket_size = int(request.GET.get("row_bucket_size", 10000))
    split_mode = str(request.GET.get("split_mode") or "").strip().lower() == "chunked"
    split_size = max(1, int(request.GET.get("split_size", batch_size)))
    jobs = []

    service = SearchGatewayService(index_name=index_name)
    if not service.data_source:
        return JsonResponse({"error": "Invalid index_name"}, status=400)

    # Download workflow is isolated from the table UI and runs for selected dimension.
    dimensions = []
    current = _resolve_observation_dimension(request)
    if current:
        dimensions = [current]
    elif scope == "all" and page_id:
        try:
            page = ObservationPage.objects.get(id=int(page_id))
        except (ObservationPage.DoesNotExist, TypeError, ValueError):
            return JsonResponse({"error": "Invalid page_id"}, status=400)
        default_dimension = page.get_default_dimension_config()
        if default_dimension:
            dimensions = [default_dimension]
    if not dimensions:
        return JsonResponse({"error": "No dimensions available"}, status=400)

    for dimension in dimensions:
        slug = dimension.get("slug") or ""
        normalized_dimension = deepcopy(dimension)
        normalized_dimension["row_bucket_size"] = row_bucket_size
        query_source = request.GET.copy()
        service = SearchGatewayService(index_name=index_name)

        # "Generate all CSVs" must iterate through all records from backend,
        # split by the selected limit (1000/2000), and create sequential files.
        if split_mode:
            batch_snapshot = _store_batch_job(
                dimension=normalized_dimension,
                message=_("Starting backend export..."),
            )
            worker = threading.Thread(
                target=_run_chunked_export_async,
                kwargs={
                    "batch_job_id": batch_snapshot["id"],
                    "dimension": normalized_dimension,
                    "query_source": query_source,
                    "index_name": index_name,
                    "split_size": split_size,
                },
                daemon=True,
            )
            worker.start()
            jobs.append(batch_snapshot)
            continue

        file_slug = slug or "dimension"
        file_name = f"observation_{file_slug}_{int(time.time())}.csv"
        file_job = _store_pending_csv_job(
            dimension=normalized_dimension,
            file_name=file_name,
            message=_("Starting backend export..."),
        )
        worker = threading.Thread(
            target=_run_export_job,
            kwargs={
                "job_id": file_job["id"],
                "query_string": query_source.urlencode(),
                "index_name": index_name,
                "dimension": normalized_dimension,
                "batch_size": batch_size,
                "progress_step": progress_step,
                "export_scope": scope,
                "split_size": split_size,
            },
            daemon=True,
        )
        worker.start()
        jobs.append(file_job)
    return JsonResponse({"jobs": jobs})


@require_GET
def export_status(request, job_id):
    with EXPORT_JOBS_LOCK:
        job = EXPORT_JOBS.get(job_id)
        if not job:
            return JsonResponse({"error": "Job not found"}, status=404)
        payload = {"job": _job_snapshot(job)}
        if job.get("job_type") == "batch":
            ready_jobs = []
            for child_id in job.get("ready_file_ids") or []:
                child = EXPORT_JOBS.get(child_id)
                if child:
                    ready_jobs.append(_job_snapshot(child))
            payload["ready_jobs"] = ready_jobs
    return JsonResponse(payload)


@require_GET
def export_download(request, job_id):
    with EXPORT_JOBS_LOCK:
        job = EXPORT_JOBS.get(job_id)
    if not job:
        return JsonResponse({"error": "Job not found"}, status=404)
    if job.get("status") != "done":
        return JsonResponse({"error": "Job is not ready yet"}, status=409)
    csv_content = job.get("csv_content", "")
    if not isinstance(csv_content, str) or not csv_content.strip():
        fallback = StringIO()
        fallback_writer = csv.writer(fallback)
        fallback_writer.writerow([_("Message")])
        fallback_writer.writerow([_("No data available for export")])
        csv_content = fallback.getvalue()
    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{job.get("file_name", "observation.csv")}"'
    response["Cache-Control"] = "no-store"
    return response
