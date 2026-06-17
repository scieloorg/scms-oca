import logging

from django.conf import settings
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from .advance_search import AdvancedQueryValidationError
from search_gateway.request_filters import (
    extract_applied_filters,
    normalize_option_filters,
)
from search_gateway.service import SearchGatewayService

from .models import SearchPage


def _render_results_fragments(request, results_data, *, has_citations_field=False):
    context = {
        "results_data": results_data, 
        "has_citations_field": has_citations_field
    }

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

        results_data = SearchPage.search_documents_with_retry(
            service,
            request_state,
            selected_filters,
        )

        results_data = SearchPage.current_pagination(
            results_data,
            page=request_state["current_page"],
            page_size=request_state["current_limit"],
            current_sort=request_state["current_sort"],
        )

        has_citations_field = bool(data_source.get_field("cited_by_count_range"))
        fragments = _render_results_fragments(request, results_data, has_citations_field=has_citations_field)

        return JsonResponse({
            **fragments,
            "current_page": results_data.get("current_page"),
            "citation_documents": SearchPage.build_citation_documents(
                results_data.get("search_results")
            ),
        })

    except AdvancedQueryValidationError as e:
        return JsonResponse({"error": str(e), "error_type": "advanced_query"}, status=400)

    except Exception as e:
        logging.exception(f"Error getting filters for index {index_name}. {e}")
        return JsonResponse({"error": str(e)}, status=500)
