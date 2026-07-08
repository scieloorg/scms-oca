from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from wagtail.admin import messages
from wagtail.admin.auth import permission_denied, require_admin_access

from etl.models import EtlItemProcess, EtlPipelineConfig, EtlStatus
from etl.presentation import build_etl_summary_stats, format_document_type_label
from etl.tasks import process_pending_silver_etl


def _redirect_back(request):
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


def _execute_etl_action(request, action_type, document_type):
    if document_type not in EtlPipelineConfig.objects.enabled_document_types():
        messages.error(
            request,
            _("Invalid document type: %(doc_type)s") % {"doc_type": document_type},
        )
        return _redirect_back(request)

    already_running = EtlItemProcess.objects.filter(
        document_type=document_type,
        status=EtlStatus.PROCESSING,
    ).exists()
    if already_running:
        messages.warning(
            request,
            _("A task is already running for '%(doc_type)s'. Please wait for it to finish.")
            % {"doc_type": format_document_type_label(document_type)},
        )
        return _redirect_back(request)

    if action_type == "retry_failed":
        rows = EtlItemProcess.objects.retry_failed_by_type(document_type)
        messages.success(
            request,
            _("%(count)s failed item(s) of type '%(doc_type)s' reset to pending.")
            % {"count": rows, "doc_type": format_document_type_label(document_type)},
        )

    try:
        result = process_pending_silver_etl.delay(document_type=document_type)
    except Exception as error:
        messages.error(
            request,
            _("Could not enqueue the ETL task: %(error)s") % {"error": error},
        )
        return _redirect_back(request)

    messages.success(
        request,
        _("Pending ETL triggered for '%(doc_type)s'. Task ID: %(task_id)s")
        % {"doc_type": document_type, "task_id": result.id},
    )
    return _redirect_back(request)


@require_admin_access
def summary_view(request):
    if not request.user.has_perm("etl.view_etlitemprocess"):
        return permission_denied(request)

    stats = build_etl_summary_stats(
        EtlItemProcess.objects.get_summary_stats(),
        EtlPipelineConfig.objects.enabled_document_types(),
        EtlPipelineConfig.objects.source_index_by_document_type(),
        EtlPipelineConfig.objects.match_index_by_document_type(),
    )

    return render(
        request,
        "etl/admin/summary.html",
        {
            "stats": stats,
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


@require_admin_access
@require_POST
def trigger_pending_by_type_view(request):
    if not request.user.has_perm("etl.change_etlitemprocess"):
        return permission_denied(request)

    document_type = request.POST.get("type")
    if not document_type:
        return HttpResponseBadRequest("Missing 'type' parameter")

    return _execute_etl_action(request, "trigger_pending", document_type)


@require_admin_access
@require_POST
def retry_failed_by_type_view(request):
    if not request.user.has_perm("etl.change_etlitemprocess"):
        return permission_denied(request)

    document_type = request.POST.get("type")
    if not document_type:
        return HttpResponseBadRequest("Missing 'type' parameter")

    return _execute_etl_action(request, "retry_failed", document_type)
