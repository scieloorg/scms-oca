from django.http import JsonResponse
from django.views.decorators.http import require_GET

from . import controller
from .client import get_opensearch_client


def _parse_bool_param(value):
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


@require_GET
def filters_view(request):
    data_source = request.GET.get('data_source')
    fields_param = request.GET.get("fields", "")
    include_fields = [item.strip() for item in fields_param.split(",") if item.strip()]
    refresh = _parse_bool_param(request.GET.get("refresh"))
    excluded_query_keys = {"data_source", "fields", "refresh"}
    requested_filters = {}

    for key in request.GET.keys():
        if key in excluded_query_keys:
            continue
        values = [value for value in request.GET.getlist(key) if value not in (None, "")]
        if not values:
            continue
        requested_filters[key] = values if len(values) > 1 else values[0]

    # Backward compatibility: old URLs used source_index_open_alex to mean scope.
    if "scope" not in requested_filters and "source_index_open_alex" in requested_filters:
        requested_filters["scope"] = requested_filters.pop("source_index_open_alex")

    filters, error = controller.get_filters_data(
        data_source,
        include_fields=include_fields,
        force_refresh=refresh,
        filters=requested_filters,
    )
    if error:
        return JsonResponse({"error": error}, status=500)
    return JsonResponse(filters)


@require_GET
def search_item_view(request):
    q = request.GET.get("q", "")
    data_source_name = request.GET.get("data_source", "journal_metrics")
    field_name = request.GET.get("field_name", "journal")
    excluded_query_keys = {"q", "data_source", "field_name"}
    requested_filters = {}
    
    for key in request.GET.keys():
        if key in excluded_query_keys:
            continue
        values = [value for value in request.GET.getlist(key) if value not in (None, "")]
        if not values:
            continue
        requested_filters[key] = values if len(values) > 1 else values[0]
    results, error = controller.search_item(
        q,
        data_source_name,
        field_name,
        filters=requested_filters,
    )
    if error:
        status_code = 503 if error == "Service unavailable" else 400 if error == "Invalid data_source" else 500
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(results)


@require_GET
def search_as_you_type_view(request):
    q = request.GET.get("q", "")
    data_source_name = request.GET.get("index_name")
    field_name = request.GET.get("field_name", "")
    client = get_opensearch_client()
    try:
        results = controller.search_as_you_type(data_source_name, q, field_name, client=client)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500) # TODO: Handle different error codes
    return JsonResponse(results, safe=False)
