import logging

from django.conf import settings
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from search_gateway.filter_ui import render_filter_sidebar
from search_gateway.request_filters import (
    extract_applied_filters,
    normalize_option_filters,
)
from search_gateway.service import SearchGatewayService

from .models import SearchPage


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
        results_html = render_to_string(
            "search/include/results_list.html",
            {"results_data": results_data},
            request=request,
        )
        sidebar_payload = render_filter_sidebar(
            request,
            data_source=data_source,
            form_key="search",
            applied_filters=applied_filters,
            sidebar_form_id="search-filter-form",
            sidebar_form_method="get",
            submit_label=_("APLICAR"),
            reset_label=_("LIMPAR"),
            submit_id="search-filter-submit",
            reset_id="search-filter-reset",
            reset_type="button",
        )
        return JsonResponse({
            "total_results": results_data.get("total_results", 0),
            "results_html": results_html,
            "sidebar_html": sidebar_payload["form_html"],
            "selected_filters": selected_filters,
        })
    except Exception as e:
        logging.exception(f"Error getting filters for index {index_name}. {e}")
        return JsonResponse({"error": str(e)}, status=500)
