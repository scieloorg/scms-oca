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


def _build_country_year_aggs(*, country_field, year_field, country_size, year_size):
    return {
        "by_country": {
            "terms": {"field": country_field, "size": country_size},
            "aggs": {
                "by_year": {
                    "terms": {"field": year_field, "size": year_size},
                },
            },
        },
    }


def _parse_query_clauses(request):
    raw = request.GET.get("search_clauses")
    if not raw:
        return []
    try:
        clauses = json.loads(raw)
        return clauses if isinstance(clauses, list) else []
    except (json.JSONDecodeError, TypeError):
        return []

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

        field_settings = service.data_source.field_settings_dict or {}
        country_cfg = field_settings.get("country", {})
        year_cfg = field_settings.get("publication_year", {})
        country_field = country_cfg.get("index_field_name", "author_country_codes")
        year_field = year_cfg.get("index_field_name", "publication_year")
        country_size = country_cfg.get("filter", {}).get("size", 500)
        year_size = year_cfg.get("filter", {}).get("size", 300)

        aggs = _build_country_year_aggs(
            country_field=country_field,
            year_field=year_field,
            country_size=country_size,
            year_size=year_size,
        )

        parse_config = {
            "row_agg_name": "by_country",
            "col_agg_name": "by_year",
            "row_display_transform": "country",
            "row_field_name": "country",
        }

        result = service.search_aggregation(
            aggs=aggs,
            query_text=text_search if not query_clauses else None,
            query_clauses=query_clauses if query_clauses else None,
            filters=selected_filters,
            parse_config=parse_config,
        )
        return JsonResponse(result)
    except Exception as e:
        logger.exception("Error in observation api_country_year_table: %s", e)
        return JsonResponse(
            {"error": str(e), "columns": [], "rows": [], "grand_total": 0},
            status=500,
        )
