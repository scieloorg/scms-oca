import json
import logging
from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from search_gateway.forms import render_filter_sidebar
from search_gateway.models import DataSource
from search_gateway.request_filters import extract_applied_filters
from search_gateway.request_filters import normalize_option_filters
from search_gateway.service import SearchGatewayService

from .models import SearchPage


@require_GET
def search_page_by_index(request, index_name):
    data_source = DataSource.get_by_index_name(index_name=index_name)
    if not data_source:
        raise Http404("Search data source does not exist")

    context = SearchPage._build_search_context_for_data_source(request, data_source)
    return render(request, "search/search_page.html", context)

@require_GET
def search_view_list(request):
    index_name = request.GET.get(
        "index_name",
        getattr(settings, "OP_INDEX_SCIENTIFIC_PRODUCTION", "scientific_production"),
    )
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("limit", 25))
    current_sort = request.GET.get("sort", "recent")
    text_search = request.GET.get("search", "")
    query_clauses = SearchPage.query_clauses(request)

    try:
        service = SearchGatewayService(index_name=index_name)
        data_source = service.data_source
        applied_filters = extract_applied_filters(request.GET, data_source, form_key="search")
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
        results_data = SearchPage.enrich_results_data_for_display(data_source, results_data)
        results_data = SearchPage.decorate_results_data_for_ui(
            results_data,
            page=page,
            page_size=page_size,
            sort=current_sort,
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
