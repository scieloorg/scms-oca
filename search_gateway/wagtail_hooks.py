from django.core.exceptions import PermissionDenied
from django.templatetags.static import static
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.widgets.button import Button
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .metric_preview import build_metric_preview
from .models import DataSource


class DataSourceSnippetViewSet(SnippetViewSet):
    model = DataSource
    icon = "search"
    menu_label = _("Data Sources")
    add_to_admin_menu = True
    menu_order = 200
    list_display = ("index_name", "display_name")
    search_fields = ("index_name", "display_name")

    def get_urlpatterns(self):
        return super().get_urlpatterns() + [
            path("metric-preview/<str:pk>/", self.metric_preview_view, name="metric_preview"),
        ]

    def metric_preview_view(self, request, pk):
        if not request.user.has_perm("search_gateway.change_datasource"):
            raise PermissionDenied

        data_source = get_object_or_404(DataSource, pk=pk)
        study_unit = request.GET.get("study_unit") or "document"
        preview = build_metric_preview(data_source, study_unit=study_unit)
        return render(
            request,
            "search_gateway/admin/metric_preview.html",
            {
                "data_source": data_source,
                "preview": preview,
            },
        )

register_snippet(DataSourceSnippetViewSet)


@hooks.register("construct_snippet_listing_buttons")
def add_data_source_metric_preview_button(buttons, instance, user):
    if not isinstance(instance, DataSource):
        return
    if not user.has_perm("search_gateway.change_datasource"):
        return

    buttons.append(
        Button(
            _("Metric preview"),
            reverse(
                "wagtailsnippets_search_gateway_datasource:metric_preview",
                args=[instance.pk],
            ),
            icon_name="view",
            priority=50,
        )
    )



@hooks.register('insert_global_admin_css')
def global_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static('css/admin_custom.css')
    )
