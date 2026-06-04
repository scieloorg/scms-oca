from django.http import JsonResponse
from search_gateway.models import DataSource
from indicator_journal.metrics.engine import JournalMetricEngine


def journal_profile_options_view(request):
    issn = str(request.GET.get("issn") or request.GET.get("journal") or "").strip()
    if not issn:
        return JsonResponse({"error": "Missing journal identifier"}, status=400)

    data_source_name = str(request.GET.get("data_source") or "").strip()
    if not data_source_name:
        return JsonResponse({"error": "Missing data_source"}, status=400)

    data_source = DataSource.get_by_index_name(index_name=data_source_name)
    if not data_source:
        return JsonResponse({"error": f"DataSource '{data_source_name}' not found"}, status=400)

    engine = JournalMetricEngine(data_source)
    profile_data, error = engine.get_profile_timeseries(
        issn=issn,
        category_level=request.GET.get("category_level"),
        category_id=request.GET.get("category_id"),
        publication_year=request.GET.get("publication_year"),
        form_filters={
            "collection": request.GET.get("collection"),
        },
    )
    if error:
        return JsonResponse({"error": error}, status=400)

    return JsonResponse(
        {
            "available_categories": (profile_data or {}).get("available_categories") or [],
            "available_category_levels": (profile_data or {}).get("available_category_levels") or [],
            "selected_category_id": (profile_data or {}).get("selected_category_id") or "",
            "selected_category_level": (profile_data or {}).get("selected_category_level") or "",
        }
    )
