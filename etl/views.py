from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from wagtail.admin import messages
from wagtail.admin.auth import permission_denied, require_admin_access

from etl.models import EtlItemProcess, EtlStatus

DOCUMENT_TYPES = (
    "article",
    "book",
    "preprint",
    "dataset",
)
STATUS_FIELDS = (
    EtlStatus.PENDING,
    EtlStatus.PROCESSING,
    EtlStatus.SUCCESS,
    EtlStatus.FAILED,
    EtlStatus.SKIPPED,
)
DOCUMENT_TYPE_LABELS = {
    "article": _("Articles"),
    "book": _("Books"),
    "preprint": _("Preprints"),
    "dataset": _("Datasets"),
}


def _compute_stats():
    raw_stats = EtlItemProcess.objects.get_summary_stats()
    status_counts = raw_stats.get("status_counts", {})
    type_counts = raw_stats.get("type_counts", {})
    type_status_counts = raw_stats.get("type_status_counts", {})
    scielo_dedup_counts = raw_stats.get("scielo_dedup_counts", {})
    openalex_counts = raw_stats.get("openalex_counts", {})

    total_scielo_dedup = sum(scielo_dedup_counts.values())
    total_openalex = sum(openalex_counts.values())

    return {
        "total": sum(status_counts.values()),
        "pending": status_counts.get(EtlStatus.PENDING, 0),
        "processing": status_counts.get(EtlStatus.PROCESSING, 0),
        "success": status_counts.get(EtlStatus.SUCCESS, 0),
        "failed": status_counts.get(EtlStatus.FAILED, 0),
        "skipped": status_counts.get(EtlStatus.SKIPPED, 0),
        "scielo_dedup": total_scielo_dedup,
        "openalex": total_openalex,
        "by_type": {dt: type_counts.get(dt, 0) for dt in DOCUMENT_TYPES},
        "by_type_rows": [
            {
                "key": document_type,
                "label": DOCUMENT_TYPE_LABELS[document_type],
                "total": type_counts.get(document_type, 0),
                "scielo_dedup": scielo_dedup_counts.get(document_type, 0),
                "openalex": openalex_counts.get(document_type, 0),
                **{
                    status: type_status_counts.get((document_type, status), 0)
                    for status in STATUS_FIELDS
                },
            }
            for document_type in DOCUMENT_TYPES
        ],
    }


def _processing_already_running(document_type, request) -> bool:
    if EtlItemProcess.objects.filter(
        document_type=document_type,
        status=EtlStatus.PROCESSING,
    ).exists():
        messages.warning(
            request,
            _("Já existe uma task em execução para '%(doc_type)s'. Aguarde a conclusão.") % {"doc_type": DOCUMENT_TYPE_LABELS.get(document_type, document_type)},
        )
        return True
    return False


@require_admin_access
def summary_view(request):
    if not request.user.has_perm("etl.view_etlitemprocess"):
        return permission_denied(request)

    return render(
        request,
        "etl/admin/summary.html",
        {
            "stats": _compute_stats(),
            "list_url": reverse("wagtailsnippets_etl_etlitemprocess:list"),
            "header_title": _("ETL Summary"),
            "header_icon": "tasks",
            "breadcrumbs_items": [
                {"url": reverse("wagtailadmin_home"), "label": _("Home")},
                {"url": "", "label": _("ETL Summary")},
            ],
            "trigger_pending_by_type_url": reverse("etl_trigger_pending_by_type"),
            "retry_failed_by_type_url": reverse("etl_retry_failed_by_type"),
        },
    )


@require_POST
def trigger_pending_view(request):
    from etl.tasks import process_pending_silver_etl

    result = process_pending_silver_etl.delay(limit=5000)
    messages.success(request, f"Pending ETL triggered. Task ID: {result.id}")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


@require_POST
def trigger_pending_by_type_view(request):
    from etl.tasks import process_pending_silver_etl

    document_type = request.POST.get("type", "preprint")
    if document_type not in DOCUMENT_TYPES:
        messages.error(request, f"Invalid document type: {document_type}")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))
    if _processing_already_running(document_type, request):
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))
    result = process_pending_silver_etl.delay(limit=5000, document_type=document_type)
    messages.success(
        request,
        f"Pending ETL triggered for '{document_type}'. Task ID: {result.id}",
    )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


@require_POST
def retry_failed_by_type_view(request):
    from etl.tasks import process_pending_silver_etl

    document_type = request.POST.get("type", "preprint")
    if document_type not in DOCUMENT_TYPES:
        messages.error(request, f"Invalid document type: {document_type}")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))
    if _processing_already_running(document_type, request):
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))
    rows = EtlItemProcess.objects.retry_failed_by_type(document_type)
    messages.success(request, _("%(count)s failed item(s) of type '%(doc_type)s' reset to pending.") % {"count": rows, "doc_type": document_type})
    result = process_pending_silver_etl.delay(limit=5000, document_type=document_type)
    messages.success(
        request,
        f"Pending ETL triggered for '{document_type}'. Task ID: {result.id}",
    )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


@require_POST
def retry_failed_view(request):
    ids = request.POST.get("ids", "")
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        rows = EtlItemProcess.objects.retry_failed(id_list)
        messages.success(request, _("%(count)s failed item(s) marked for retry.") % {"count": rows})
    return redirect(request.META.get("HTTP_REFERER", "/admin/"))
