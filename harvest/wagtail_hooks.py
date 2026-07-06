from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.ui.tables import BooleanColumn
from wagtail.admin.widgets.button import Button
from wagtail.log_actions import log
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView as SnippetCreateView
from wagtail.snippets.views.snippets import EditView as SnippetEditView
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .bronze_transform import transform_document
from .models import (
    GlobalMetricsUploadFile,
    HarvestedArticle,
    HarvestedBooks,
    HarvestedPreprint,
    HarvestedSciELOData,
    TransformationScript,
)


class CommonControlFieldCreateView(SnippetCreateView):
    def save_instance(self):
        instance = self.form.save_all(self.request.user)
        log(instance=instance, action="wagtail.create", content_changed=True)
        return instance


class CommonControlFieldEditView(SnippetEditView):
    def save_instance(self):
        instance = self.form.save_all(self.request.user)
        self.has_content_changes = self.form.has_changed()
        log(
            instance=instance,
            action="wagtail.edit",
            content_changed=self.has_content_changes,
        )
        return instance


class HarvestedPreprintViewSet(SnippetViewSet):
    model = HarvestedPreprint
    icon = "doc-full"
    menu_label = _("Preprint")
    add_to_admin_menu = False
    add_view_class = CommonControlFieldCreateView
    edit_view_class = CommonControlFieldEditView
    list_display = ("identifier", "harvest_status", "index_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status")
    ordering = ("-created",)


class HarvestedArticleViewSet(SnippetViewSet):
    model = HarvestedArticle
    icon = "doc-full"
    menu_label = _("Articles")
    add_to_admin_menu = False
    add_view_class = CommonControlFieldCreateView
    edit_view_class = CommonControlFieldEditView
    list_display = ("identifier", "harvest_status", "index_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status")
    ordering = ("-created",)


class HarvestedSciELODataViewSet(SnippetViewSet):
    model = HarvestedSciELOData
    icon = "doc-full"
    menu_label = _("SciELO Data")
    add_to_admin_menu = False
    add_view_class = CommonControlFieldCreateView
    edit_view_class = CommonControlFieldEditView
    list_display = ("identifier", "harvest_status", "index_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")
    ordering = ("-created",)


class HarvestedBooksViewSet(SnippetViewSet):
    model = HarvestedBooks
    icon = "doc-full"
    menu_label = _("Books")
    add_to_admin_menu = False
    add_view_class = CommonControlFieldCreateView
    edit_view_class = CommonControlFieldEditView
    list_display = ("identifier", "type_data", "harvest_status", "index_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")
    ordering = ("-created",)


class TransformationScriptViewSet(SnippetViewSet):
    model = TransformationScript
    icon = "code"
    menu_label = _("Scripts de Transformação")
    add_to_admin_menu = False
    add_view_class = CommonControlFieldCreateView
    edit_view_class = CommonControlFieldEditView
    list_display = ("name", "source_index", "dest_index", "is_active", "updated")
    search_fields = ("name", "description", "source_index", "dest_index")
    list_filter = ("is_active",)
    ordering = ("name",)


class GlobalMetricsUploadFileViewSet(SnippetViewSet):
    model = GlobalMetricsUploadFile
    icon = "upload"
    menu_label = _("Arquivos de Métricas Globais")
    add_to_admin_menu = False
    add_view_class = CommonControlFieldCreateView
    edit_view_class = CommonControlFieldEditView
    list_display = (
        "file",
        BooleanColumn("status", label=_("Processado")),
        "created",
        "updated",
    )
    list_filter = ("status", "created")
    search_fields = ("file",)
    ordering = ("-created",)


class HarvestViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Harvest")
    menu_icon = "download"
    menu_order = 84
    items = (
        HarvestedArticleViewSet,
        HarvestedPreprintViewSet,
        HarvestedSciELODataViewSet,
        HarvestedBooksViewSet,
        TransformationScriptViewSet,
        GlobalMetricsUploadFileViewSet,
    )


register_snippet(HarvestViewSetGroup)


@hooks.register("register_snippet_listing_buttons")
def register_transformation_script_listing_buttons(snippet, user, next_url=None):
    if isinstance(snippet, GlobalMetricsUploadFile):
        yield Button(
            _("Aplicar métricas globais"),
            reverse("harvest_apply_global_metrics_upload", args=[snippet.pk]),
            icon_name="tasks",
            attrs={"title": _("Aplicar métricas globais no índice silver")},
            priority=20,
        )
        return

    if not isinstance(snippet, TransformationScript):
        return

    yield Button(
        _("Executar Transformação"),
        reverse("harvest_run_transform") + f"?script_id={snippet.pk}",
        icon_name="download",
        attrs={"title": _("Executar Transformação")},
        priority=20,
    )


def apply_global_metrics_upload_view(request, upload_file_id):
    upload_file = get_object_or_404(GlobalMetricsUploadFile, pk=upload_file_id)
    if not upload_file.status:
        messages.warning(
            request,
            "O arquivo ainda não foi processado. Aguarde a indexação do upload antes de aplicar as métricas. Atualize a página e verifique a coluna 'Processado'.",
        )
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))

    from .tasks import apply_global_metrics_upload_to_silver

    result = apply_global_metrics_upload_to_silver.delay(upload_file.pk)
    messages.success(
        request,
        f"Aplicação de métricas globais enfileirada para {upload_file}. Tarefa: {result.id}.",
    )
    return redirect(request.META.get("HTTP_REFERER", "/admin/"))


def run_transform_view(request):
    """View para executar transformação de um script."""
    script_id = request.GET.get("script_id")
    if not script_id:
        messages.error(request, "ID do script não fornecido.")
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))

    script = get_object_or_404(TransformationScript, pk=script_id)

    if not script.is_active:
        messages.warning(request, f"O script '{script.name}' está desativado.")
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))

    try:
        success = transform_document(script)
        message = success.get("message")
        if success.get("status") == "success":
            messages.success(
                request,
                f"Transformação executada com sucesso: {script.source_index} → {script.dest_index}. ({message})",
            )
        else:
            messages.error(request, f"Falha na transformação. {message}")
    except Exception as exc:
        messages.error(request, f"Erro ao executar transformação: {str(exc)}")

    return redirect(request.META.get("HTTP_REFERER", "/admin/"))


@hooks.register("register_admin_urls")
def register_harvest_urls():
    return [
        path("harvest/run-transform/", run_transform_view, name="harvest_run_transform"),
        path(
            "harvest/global-metrics-upload/<int:upload_file_id>/apply/",
            apply_global_metrics_upload_view,
            name="harvest_apply_global_metrics_upload",
        ),
    ]
