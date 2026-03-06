import logging

from django.conf import settings
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from search_gateway.service import SearchGatewayService


@require_GET
def search_view_list(request):
    index_name = request.GET.get(
        "index_name",
        getattr(settings, "OP_INDEX_ALL_BRONZE", "sci*"),
    )
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("limit", 25))
    text_search = request.GET.get("search", "")
    try:
        service = SearchGatewayService(index_name=index_name)
        selected_filters = service.extract_selected_filters(request)
        results_data = service.search_documents(
            query_text=text_search,
            filters=selected_filters,
            page=page,
            page_size=page_size,
            sort_field="publication_year",
            sort_order="desc",
        )
        results_html = render_to_string(
            "search/include/results_list.html",
            {"results_data": results_data},
            request=request,
        )
        return JsonResponse({
            "total_results": results_data.get("total_results", 0),
            "results_html": results_html,
            "selected_filters": selected_filters,
        })
    except Exception as e:
        logging.exception(f"Error getting filters for index {index_name}. {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_filters_for_data_source(request):
    """
    API endpoint to get filters and metadata for a specific data source.
    Used when switching data sources in the search page.
    """
    index_name = request.GET.get(
        "index_name",
        getattr(settings, "OP_INDEX_ALL_BRONZE", "sci*"),
    )

    try:
        service = SearchGatewayService(index_name=index_name)
        filters = service.build_filters()
        filter_metadata = service.get_filter_metadata(filters)
        return JsonResponse({
            "filters": filters,
            "filter_metadata": filter_metadata,
        })
    except Exception as e:
        logging.exception(f"Error getting filters for index {index_name}. {e}")
        return JsonResponse({"error": str(e)}, status=500)