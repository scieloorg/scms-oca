from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from wagtail.admin import messages
from wagtail.admin.auth import permission_denied, require_admin_access

from enrichment.models import WorldRegionsStatus, WorldRegionsUpload
from enrichment.tasks import apply_world_regions_upload


@require_admin_access
def apply_world_regions_view(request, upload_id):
    if not request.user.has_perm("enrichment.change_worldregionsupload"):
        return permission_denied(request)

    upload = get_object_or_404(WorldRegionsUpload, pk=upload_id)

    with transaction.atomic():
        WorldRegionsUpload.objects.filter(active=True).exclude(pk=upload.pk).update(
            active=False
        )
        upload.active = True
        upload.status = WorldRegionsStatus.PENDING
        upload.task_id = ""
        upload.current_index = ""
        upload.current_task_id = ""
        upload.stats = {}
        upload.started_at = None
        upload.finished_at = None

        upload.save(
            update_fields=[
                "active",
                "status",
                "task_id",
                "current_index",
                "current_task_id",
                "stats",
                "started_at",
                "finished_at",
                "updated",
            ]
        )

    try:
        result = apply_world_regions_upload.delay(upload.pk)
    except Exception as error:
        upload.status = WorldRegionsStatus.FAILED
        upload.finished_at = timezone.now()
        upload.save(update_fields=["status", "finished_at", "updated"])
        messages.error(
            request,
            _("Não foi possível enfileirar a aplicação: %(error)s") % {"error": error},
        )
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))

    upload.task_id = result.id
    upload.save(update_fields=["task_id", "updated"])
    messages.success(
        request,
        _("Aplicação enfileirada. Tarefa: %(task_id)s") % {"task_id": result.id},
    )

    return redirect(reverse("enrichment_world_regions_results", args=[upload.pk]))


@require_admin_access
def world_regions_results_view(request, upload_id):
    if not request.user.has_perm("enrichment.view_worldregionsupload"):
        return permission_denied(request)

    upload = get_object_or_404(WorldRegionsUpload, pk=upload_id)
    duration = None
    if upload.started_at:
        duration = (upload.finished_at or timezone.now()) - upload.started_at

    return render(
        request,
        "enrichment/admin/world_regions_results.html",
        {
            "upload": upload,
            "stats": upload.stats or {},
            "duration": duration,
            "list_url": reverse("wagtailsnippets_enrichment_worldregionsupload:list"),
            "header_title": _("Resultados de World Regions"),
            "header_icon": "globe",
            "breadcrumbs_items": [
                {"url": reverse("wagtailadmin_home"), "label": _("Início")},
                {
                    "url": reverse(
                        "wagtailsnippets_enrichment_worldregionsupload:list"
                    ),
                    "label": _("Regiões Mundiais"),
                },
                {"url": "", "label": str(upload)},
            ],
        },
    )
