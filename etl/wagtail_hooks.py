from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from etl.bulk_actions import ResetToPendingBulkAction
from etl.models import EtlItemProcess, EtlPipelineConfig
from etl.presentation import format_document_type_label
from etl.views import (
    retry_failed_by_type_view,
    summary_view,
    trigger_pending_by_type_view,
)


class EtlItemProcessViewSet(SnippetViewSet):
    model = EtlItemProcess
    icon = "tasks"
    menu_label = _("Processing Items")
    add_to_admin_menu = False
    menu_order = 900

    list_display = (
        "external_id",
        "doi",
        "document_type",
        "source_index",
        "publication_year",
        "status",
        "result",
        "has_openalex_match",
        "has_scielo_dedup",
        "attempts",
        "processed_at",
    )
    list_filter = (
        "status",
        "result",
        "document_type",
        "source_index",
        "has_openalex_match",
        "has_scielo_dedup",
    )
    search_fields = (
        "external_id",
        "pid_v2",
        "doi",
        "isbn",
        "preprint_id",
        "dataset_id",
        "source_index",
    )
    ordering = ("-updated_at",)
    list_per_page = 50


register_snippet(EtlItemProcessViewSet)

etl_item_process_viewset = EtlItemProcessViewSet()


class EtlPipelineConfigViewSet(SnippetViewSet):
    model = EtlPipelineConfig
    icon = "cog"
    menu_label = _("Pipeline Configs")
    add_to_admin_menu = False
    menu_order = 901
    list_display = (
        "name",
        "enabled",
        "input_index",
        "default_document_type",
        "deduplicate_scielo",
    )
    list_filter = ("enabled", "default_document_type", "deduplicate_scielo")
    search_fields = ("name", "input_index")
    ordering = ("name",)


register_snippet(EtlPipelineConfigViewSet)


class EtlMenuItem(MenuItem):
    def is_shown(self, request):
        return etl_item_process_viewset.permission_policy.user_has_any_permission(
            request.user,
            {"add", "change", "delete", "view"},
        )


@hooks.register("register_admin_menu_item")
def register_etl_menu():
    list_url = reverse("wagtailsnippets_etl_etlitemprocess:list")

    items = [
        EtlMenuItem(
            _("Summary"),
            reverse("etl_summary"),
            icon_name="tasks",
            order=1,
        ),
    ]

    for index, document_type in enumerate(
        EtlPipelineConfig.objects.enabled_document_types()
    ):
        items.append(
            EtlMenuItem(
                format_document_type_label(document_type),
                f"{list_url}?document_type={document_type}",
                icon_name="doc-full",
                order=2 + index,
            )
        )

    items.append(
        EtlMenuItem(
            _("Pipeline Configs"),
            reverse("wagtailsnippets_etl_etlpipelineconfig:list"),
            icon_name="cog",
            order=100,
        )
    )

    return SubmenuMenuItem(
        _("ETL"),
        Menu(items=items),
        icon_name="tasks",
        name="etl",
        order=85,
    )


@hooks.register("register_admin_urls")
def register_etl_urls():
    return [
        path("etl/summary/", summary_view, name="etl_summary"),
        path("etl/trigger-pending-by-type/", trigger_pending_by_type_view, name="etl_trigger_pending_by_type"),
        path("etl/retry-failed-by-type/", retry_failed_by_type_view, name="etl_retry_failed_by_type"),
    ]


hooks.register("register_bulk_action", ResetToPendingBulkAction)
