from django.http import JsonResponse
from django.views.decorators.http import require_GET

from . import controller


@require_GET
def filters_view(request):
    data_source = request.GET.get('data_source')
    filters, error = controller.get_filters_data(data_source)
    if error:
        return JsonResponse({"error": error}, status=500)
    return JsonResponse(filters)


@require_GET
def search_item_view(request):
    q = request.GET.get("q", "")
    data_source_name = request.GET.get("data_source", "journal_metrics")
    field_name = request.GET.get("field_name", "journal")

    results, error = controller.get_search_item_results(q, data_source_name, field_name)
    if error:
        status_code = 503 if error == "Service unavailable" else 400 if error == "Invalid data_source" else 500
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(results)
