from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from wagtail import hooks
from wagtail.admin.auth import permission_denied, require_admin_access
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from etl.models import EtlItemProcess, EtlStatus


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


def _summary_stats() -> dict:
    raw_stats = EtlItemProcess.objects.get_summary_stats()
    status_counts = raw_stats["status_counts"]
    type_counts = raw_stats["type_counts"]
    return {
        "total": sum(status_counts.values()),
        "pending": status_counts.get(EtlStatus.PENDING, 0),
        "processing": status_counts.get(EtlStatus.PROCESSING, 0),
        "success": status_counts.get(EtlStatus.SUCCESS, 0),
        "failed": status_counts.get(EtlStatus.FAILED, 0),
        "skipped": status_counts.get(EtlStatus.SKIPPED, 0),
        "by_type": sorted(type_counts.items()),
    }


@hooks.register("register_admin_menu_item")
def register_etl_menu():
    list_url = reverse("wagtailsnippets_etl_etlitemprocess:list")
    submenu = Menu(
        items=[
            EtlMenuItem(_("Summary"), reverse("etl_summary"), icon_name="tasks", order=1),
            EtlMenuItem(_("Processing Items"), list_url, icon_name="list-ul", order=2),
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
            "stats": _summary_stats(),
            "list_url": reverse("wagtailsnippets_etl_etlitemprocess:list"),
            "header_title": _("ETL Summary"),
            "header_icon": "tasks",
            "breadcrumbs_items": [
                {"url": reverse("wagtailadmin_home"), "label": _("Home")},
                {"url": "", "label": _("ETL Summary")},
            ],
        },
    )


@require_POST
def reset_to_pending_view(request):
    ids = request.POST.get("ids", "")
    if ids:
        id_list = [int(item) for item in ids.split(",") if item.strip().isdigit()]
        EtlItemProcess.objects.reset_to_pending(id_list)
    return redirect(request.META.get("HTTP_REFERER", "/admin/"))


@require_POST
def retry_failed_view(request):
    ids = request.POST.get("ids", "")
    if ids:
        id_list = [int(item) for item in ids.split(",") if item.strip().isdigit()]
        EtlItemProcess.objects.retry_failed(id_list)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


@hooks.register("register_admin_urls")
def register_etl_urls():
    return [
        path("etl/summary/", summary_view, name="etl_summary"),
        path("etl/reset-pending/", reset_to_pending_view, name="etl_reset_pending"),
        path("etl/retry-failed/", retry_failed_view, name="etl_retry_failed"),
    ]
