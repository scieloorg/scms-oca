from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.ui.tables import BooleanColumn, Column
from wagtail.admin.widgets.button import Button
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from enrichment.models import WorldRegionsUpload
from enrichment.views import apply_world_regions_view, world_regions_results_view


class WorldRegionsUploadViewSet(SnippetViewSet):
    model = WorldRegionsUpload
    icon = "globe"
    menu_label = _("Regiões Mundiais")
    add_to_admin_menu = False

    list_display = (
        "file",
        BooleanColumn("active", label=_("Ativo")),
        Column(
            "status",
            label=_("Status"),
            accessor=lambda upload: upload.get_status_display(),
        ),
        Column(
            "completed_indices",
            label=_("Índices"),
            accessor=lambda upload: len(upload.stats.get("indices", [])),
        ),
        Column(
            "documents_found",
            label=_("Encontrados"),
            accessor=lambda upload: upload.stats.get("total", 0),
        ),
        Column(
            "documents_updated",
            label=_("Atualizados"),
            accessor=lambda upload: upload.stats.get("updated", 0),
        ),
        Column(
            "documents_noop",
            label=_("No-op"),
            accessor=lambda upload: upload.stats.get("noops", 0),
        ),
        Column(
            "failures",
            label=_("Falhas"),
            accessor=lambda upload: upload.stats.get("failures", 0),
        ),
        "created",
        "updated",
    )

    list_filter = ("active", "status", "created")
    search_fields = ("file",)
    ordering = ("-created",)


class EnrichmentViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Enrichment")
    menu_icon = "globe"
    menu_order = 84
    items = (WorldRegionsUploadViewSet,)


register_snippet(EnrichmentViewSetGroup)


@hooks.register("register_snippet_listing_buttons")
def register_world_regions_buttons(snippet, user, next_url=None):
    if not isinstance(snippet, WorldRegionsUpload):
        return

    yield Button(
        _("Aplicar Regiões Mundiais"),
        reverse("enrichment_apply_world_regions", args=[snippet.pk]),
        icon_name="tasks",
        priority=20,
    )

    yield Button(
        _("Ver Resultados"),
        reverse("enrichment_world_regions_results", args=[snippet.pk]),
        icon_name="view",
        priority=30,
    )


@hooks.register("register_admin_urls")
def register_enrichment_urls():
    return [
        path(
            "enrichment/world-regions/<int:upload_id>/apply/",
            apply_world_regions_view,
            name="enrichment_apply_world_regions",
        ),
        path(
            "enrichment/world-regions/<int:upload_id>/results/",
            world_regions_results_view,
            name="enrichment_world_regions_results",
        ),
    ]
