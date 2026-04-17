import logging

from django.conf import settings
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from search_gateway.request_filters import (
    extract_applied_filters,
    normalize_option_filters,
)
from search_gateway.service import SearchGatewayService

from .models import SearchPage


def _applied_filters_for_json(applied_filters):
    """Expose server-side applied filters (incl. operators) for the client without re-rendering the sidebar."""
    result = {}
    for key, value in (applied_filters or {}).items():
        if str(key).startswith("__"):
            continue
        if isinstance(value, (list, tuple)):
            cleaned = [str(item) for item in value if item not in (None, "")]
            if not cleaned:
                continue
            result[key] = cleaned if len(cleaned) > 1 else cleaned[0]
        elif value not in (None, ""):
            result[key] = str(value)
    return result


def _render_results_fragments(request, results_data):
    context = {"results_data": results_data}
    has_results = bool(results_data.get("search_results"))
    total_count = results_data.get("total_results", 0)
    return {
        "toolbar_html": render_to_string(
            "search/include/results_fragments/toolbar.html",
            {**context, "total_count": total_count},
            request=request,
        ) if has_results else "",
        "controls_html": render_to_string(
            "search/include/results_fragments/controls.html",
            context,
            request=request,
        ) if has_results else "",
        "results_list_html": render_to_string(
            "search/include/results_fragments/list.html",
            context,
            request=request,
        ),
        "pagination_html": render_to_string(
            "search/include/results_fragments/pagination.html",
            context,
            request=request,
        ) if has_results else "",
    }

@require_GET
def search_view_list(request):
    index_name = request.GET.get(
        "index_name",
        getattr(settings, "OP_INDEX_SCIENTIFIC_PRODUCTION", "scientific_production"),
    )

    try:
        service = SearchGatewayService(index_name=index_name)
        data_source = service.data_source
        request_state = SearchPage.get_search_request_state(request, data_source=data_source)
        applied_filters = extract_applied_filters(request.GET, data_source, form_key="search")
        selected_filters = normalize_option_filters(applied_filters)
        results_data = service.search_documents(
            query_text=request_state["search_query"] if not request_state["query_clauses"] else None,
            query_clauses=request_state["query_clauses"],
            filters=selected_filters,
            page=request_state["current_page"],
            page_size=request_state["current_limit"],
            sort_field=request_state["sort_field"],
            sort_order=request_state["sort_order"],
        )
        results_data = SearchPage.current_pagination(
            results_data,
            page=request_state["current_page"],
            page_size=request_state["current_limit"],
            current_sort=request_state["current_sort"],
        )
        fragments = _render_results_fragments(request, results_data)
        return JsonResponse({
            **fragments,
            "citation_documents": SearchPage.build_citation_documents(
                results_data.get("search_results")
            ),
        })
    except Exception as e:
        logging.exception(f"Error getting filters for index {index_name}. {e}")
        return JsonResponse({"error": str(e)}, status=500)
