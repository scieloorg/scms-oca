from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .forms import render_filter_sidebar
from .models import DataSource
from .request_filters import extract_applied_filters
from .service import SearchGatewayService


def _parse_bool_param(value):
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _status_code_for_error(error):
    if error == "Service unavailable":
        return 503
    if error in {"Missing data_source parameter", "Invalid data_source", "Field settings not found"}:
        return 400
    return 500


@require_GET
def filters_view(request):
    data_source_name = request.GET.get("data_source")
    if not data_source_name:
        return JsonResponse({"error": "Missing data_source parameter"}, status=400)

    include_form = _parse_bool_param(request.GET.get("include_form"))
    if include_form:
        form_key = str(request.GET.get("form") or "").strip()
        if not form_key:
            return JsonResponse({"error": "Missing form parameter"}, status=400)

        data_source = DataSource.resolve(data_source_name)
        if not data_source:
            return JsonResponse({"error": "Invalid data_source"}, status=400)

        applied_filters = extract_applied_filters(request.GET, data_source, form_key=form_key)
        payload = render_filter_sidebar(
            request,
            data_source=data_source,
            form_key=form_key,
            applied_filters=applied_filters,
        )
        return JsonResponse(
            {
                "filters": payload["options_by_field"],
                "filter_metadata": payload["filter_metadata"],
                "form_groups": payload["form_groups"],
                "form_html": payload["form_html"],
                "applied_filters": payload["applied_filters"],
                "errors": payload["errors"],
            }
        )

    fields_param = request.GET.get("fields", "")
    include_fields = [item.strip() for item in fields_param.split(",") if item.strip()]
    refresh = _parse_bool_param(request.GET.get("refresh"))
    excluded_query_keys = {"data_source", "fields", "refresh", "include_form", "form"}
    requested_filters = {}

    for key in request.GET.keys():
        if key in excluded_query_keys:
            continue
        values = [value for value in request.GET.getlist(key) if value not in (None, "")]
        if not values:
            continue
        requested_filters[key] = values if len(values) > 1 else values[0]

    service = SearchGatewayService(index_name=data_source_name)
    filters, error = service.get_filters_data(
        include_fields=include_fields,
        force_refresh=refresh,
        filters=requested_filters,
    )
    if error:
        return JsonResponse({"error": error}, status=_status_code_for_error(error))
    return JsonResponse(filters)


@require_GET
def search_item_view(request):
    q = request.GET.get("q", "")
    data_source_name = request.GET.get("data_source", "journal_metrics_by_*")
    field_name = request.GET.get("field_name", "journal_title")
    excluded_query_keys = {"q", "data_source", "field_name"}
    requested_filters = {}

    for key in request.GET.keys():
        if key in excluded_query_keys:
            continue
        values = [value for value in request.GET.getlist(key) if value not in (None, "")]
        if not values:
            continue
        requested_filters[key] = values if len(values) > 1 else values[0]

    service = SearchGatewayService(index_name=data_source_name)
    results, error = service.search_item(
        q,
        field_name,
        filters=requested_filters,
    )
    if error:
        return JsonResponse({"error": error}, status=_status_code_for_error(error))
    return JsonResponse(results)
