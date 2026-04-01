"""
Observation views - duplicated from search (searchv2) to be self-contained.
No changes to the search application.
"""
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from observation.models import ObservationPage
from search_gateway.request_filters import (
    extract_applied_filters,
    normalize_option_filters,
)
from search_gateway.service import SearchGatewayService

logger = logging.getLogger(__name__)

OBSERVATION_SEARCH_FORM_KEY = "search"


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


def _parse_query_clauses(request):
    raw = request.GET.get("search_clauses")
    if not raw:
        return []
    try:
        clauses = json.loads(raw)
        return clauses if isinstance(clauses, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _apply_lookup_labels_to_rows(service, row_field_name, result):
    if not result or not row_field_name:
        return result

    data_source = service.data_source
    if not data_source:
        return result

    resolved_field = data_source.get_field(row_field_name)
    if not resolved_field or not resolved_field.lookup:
        return result

    rows = result.get("rows") or []
    row_keys = [
        str(row.get("key")).strip()
        for row in rows
        if row.get("key") not in (None, "")
    ]
    if not row_keys:
        return result

    lookup_options, lookup_error = service.get_lookup_options_by_values(
        row_field_name,
        row_keys,
    )
    if lookup_error or not lookup_options:
        logger.warning(
            "Observation table: lookup label resolution failed for field %s: %s",
            row_field_name,
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

@require_GET
def list(request):
    index_name = _get_index_name(request)
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("limit", 25))
    text_search = request.GET.get("search", "")
    query_clauses = _parse_query_clauses(request)

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
    text_search = request.GET.get("search", "")
    query_clauses = _parse_query_clauses(request)

    try:
        service = SearchGatewayService(index_name=index_name)
        if not service.data_source:
            return JsonResponse({"columns": [], "rows": [], "grand_total": 0})
        applied_filters = extract_applied_filters(
            request.GET,
            service.data_source,
            form_key=OBSERVATION_SEARCH_FORM_KEY,
        )
        selected_filters = normalize_option_filters(applied_filters)

        dimension = _resolve_observation_dimension(request) or {
            "row_field_name": "country",
            "col_field_name": "publication_year",
            "row_bucket_size": 500,
            "col_bucket_size": 300,
        }
        field_settings = service.data_source.field_settings_dict or {}

        row_field_name = dimension.get("row_field_name") or "country"
        col_field_name = dimension.get("col_field_name") or "publication_year"
        row_cfg = field_settings.get(row_field_name, {})
        col_cfg = field_settings.get(col_field_name, {})
        row_field = row_cfg.get("index_field_name")
        col_field = col_cfg.get("index_field_name")
        if not row_field or not col_field:
            logger.warning(
                "Observation table dimension has invalid field mapping: row=%s col=%s",
                row_field_name,
                col_field_name,
            )
            return JsonResponse({"columns": [], "rows": [], "grand_total": 0})

        row_size = int(dimension.get("row_bucket_size") or row_cfg.get("filter", {}).get("size", 500))
        col_size = int(dimension.get("col_bucket_size") or col_cfg.get("filter", {}).get("size", 300))
        aggs = _build_nested_terms_aggs(
            row_field=row_field,
            col_field=col_field,
            row_size=row_size,
            col_size=col_size,
        )

        parse_config = {
            "row_agg_name": "by_row",
            "col_agg_name": "by_col",
            "row_field_name": row_field_name,
        }
        row_transform = row_cfg.get("settings", {}).get("display_transform")
        if row_transform:
            parse_config["row_display_transform"] = row_transform

        result = service.search_aggregation(
            aggs=aggs,
            query_text=text_search if not query_clauses else None,
            query_clauses=query_clauses if query_clauses else None,
            filters=selected_filters,
            parse_config=parse_config,
        )
        result = _apply_lookup_labels_to_rows(service, row_field_name, result)
        return JsonResponse(result)
    except Exception as e:
        logger.exception("Error in observation api_country_year_table: %s", e)
        return JsonResponse(
            {"error": str(e), "columns": [], "rows": [], "grand_total": 0},
            status=500,
        )
