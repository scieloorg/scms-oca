from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from wagtail.admin import messages
from wagtail.admin.auth import permission_denied, require_admin_access

from enrichment.models import WorldRegionsUpload
from enrichment.tasks import apply_world_regions_upload


@require_admin_access
def apply_world_regions_view(request, upload_id):
    if not request.user.has_perm("enrichment.change_worldregionsupload"):
        return permission_denied(request)

    upload = get_object_or_404(WorldRegionsUpload, pk=upload_id)

    with transaction.atomic():
        WorldRegionsUpload.objects.filter(
            active=True,
            target_data_source=upload.target_data_source,
        ).exclude(pk=upload.pk).update(active=False)
        upload.prepare_application()

    try:
        result = apply_world_regions_upload.delay(upload.pk)
    except Exception as error:
        upload.fail_application(
            {"errors": [str(error)]}
        )
        messages.error(
            request,
            _("Não foi possível enfileirar a aplicação: %(error)s")
            % {"error": error},
        )
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))

    messages.success(
        request,
        _("Aplicação enfileirada. Tarefa: %(task_id)s")
        % {"task_id": result.id},
    )

    return redirect("wagtailsnippets_enrichment_worldregionsupload:list")


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
