from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.auth import permission_denied, require_admin_access
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from etl.models import EtlItemProcess, EtlResult, EtlStatus
from etl.tasks import process_pending_silver_etl, run_silver_etl

DOCUMENT_TYPES = ("article", "book")
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
}


def _compute_stats():
    raw_stats = EtlItemProcess.objects.get_summary_stats()
    status_counts = raw_stats["status_counts"]
    type_counts = raw_stats["type_counts"]
    type_status_counts = raw_stats["type_status_counts"]
    merged_counts = raw_stats["merged_counts"]
    total_merged = sum(merged_counts.values())

    return {
        "total": sum(status_counts.values()),
        "pending": status_counts.get(EtlStatus.PENDING, 0),
        "processing": status_counts.get(EtlStatus.PROCESSING, 0),
        "success": status_counts.get(EtlStatus.SUCCESS, 0),
        "failed": status_counts.get(EtlStatus.FAILED, 0),
        "skipped": status_counts.get(EtlStatus.SKIPPED, 0),
        "merged": total_merged,
        "by_type": {dt: type_counts.get(dt, 0) for dt in DOCUMENT_TYPES},
        "by_type_rows": [
            {
                "key": document_type,
                "label": DOCUMENT_TYPE_LABELS[document_type],
                "total": type_counts.get(document_type, 0),
                "merged": merged_counts.get(document_type, 0),
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


class EtlItemProcessViewSet(SnippetViewSet):
    model = EtlItemProcess
    icon = "tasks"
    menu_label = _("Processing Items")
    add_to_admin_menu = False
    menu_order = 900

    list_display = (
        "external_id",
        "document_type",
        "source_index",
        "publication_year",
        "status",
        "result",
        "attempts",
        "processed_at",
    )
    list_filter = (
        "status",
        "result",
        "document_type",
        "source_index",
    )
    search_fields = (
        "external_id",
        "source_index",
    )
    ordering = ("-updated_at",)
    list_per_page = 50


register_snippet(EtlItemProcessViewSet)


class EtlMenuItem(MenuItem):
    def is_shown(self, request):
        return EtlItemProcessViewSet().permission_policy.user_has_any_permission(
            request.user,
            {"add", "change", "delete", "view"},
        )


@hooks.register("register_admin_menu_item")
def register_etl_menu():
    list_url = reverse("wagtailsnippets_etl_etlitemprocess:list")
    submenu = Menu(
        items=[
            EtlMenuItem(
                _("Summary"),
                reverse("etl_summary"),
                icon_name="tasks",
                order=1,
            ),
            *[
                EtlMenuItem(
                    label,
                    f"{list_url}?document_type={document_type}",
                    icon_name="doc-full",
                    order=2 + index,
                )
                for index, (document_type, label) in enumerate(
                    DOCUMENT_TYPE_LABELS.items()
                )
            ],
        ]
    )
    return SubmenuMenuItem(
        _("ETL"),
        submenu,
        icon_name="tasks",
        name="etl",
        order=85,
    )


@require_admin_access
def summary_view(request):
    if not EtlItemProcessViewSet().permission_policy.user_has_any_permission(
        request.user,
        {"add", "change", "delete", "view"},
    ):
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
            "trigger_pipeline_url": reverse("etl_trigger_pipeline"),
            "trigger_pending_by_type_url": reverse("etl_trigger_pending_by_type"),
            "retry_failed_by_type_url": reverse("etl_retry_failed_by_type"),
        },
    )


@require_POST
def trigger_pipeline_view(request):
    target_type = request.POST.get("type", "preprint")
    if target_type not in DOCUMENT_TYPES:
        messages.error(request, f"Invalid target type: {target_type}")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))
    if _processing_already_running(target_type, request):
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))
    result = run_silver_etl.delay(target_type=target_type)
    messages.success(
        request,
        f"ETL pipeline triggered for '{target_type}'. Task ID: {result.id}",
    )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


@require_POST
def trigger_pending_view(request):
    result = process_pending_silver_etl.delay(limit=5000)
    messages.success(request, f"Pending ETL triggered. Task ID: {result.id}")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


@require_POST
def trigger_pending_by_type_view(request):
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
def reset_to_pending_view(request):
    ids = request.POST.get("ids", "")
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        rows = EtlItemProcess.objects.reset_to_pending(id_list)
        messages.success(request, _("%(count)s item(s) reset to pending.") % {"count": rows})
    return redirect(request.META.get("HTTP_REFERER", "/admin/"))


@require_POST
def retry_failed_view(request):
    ids = request.POST.get("ids", "")
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        rows = EtlItemProcess.objects.retry_failed(id_list)
        messages.success(request, _("%(count)s failed item(s) marked for retry.") % {"count": rows})
    return redirect(request.META.get("HTTP_REFERER", "/admin/"))


@hooks.register("register_admin_urls")
def register_etl_urls():
    return [
        path("etl/summary/", summary_view, name="etl_summary"),
        path("etl/trigger-pipeline/", trigger_pipeline_view, name="etl_trigger_pipeline"),
        path("etl/trigger-pending/", trigger_pending_view, name="etl_trigger_pending"),
        path("etl/trigger-pending-by-type/", trigger_pending_by_type_view, name="etl_trigger_pending_by_type"),
        path("etl/retry-failed-by-type/", retry_failed_by_type_view, name="etl_retry_failed_by_type"),
        path("etl/reset-pending/", reset_to_pending_view, name="etl_reset_pending"),
        path("etl/retry-failed/", retry_failed_view, name="etl_retry_failed"),
    ]
