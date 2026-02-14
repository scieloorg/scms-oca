from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.admin import messages
from wagtail_modeladmin.helpers import ButtonHelper
from wagtail_modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail_modeladmin.views import CreateView

from .bronze_transform import transform_document
from .models import (
    HarvestedBooks,
    HarvestedPreprint,
    HarvestedSciELOData,
    TransformationScript,
)


class HarvestedPreprintAdmin(ModelAdmin):
    model = HarvestedPreprint
    menu_label = "Preprint"
    menu_icon = "doc-full"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status")


class HarvestedSciELODataAdmin(ModelAdmin):
    model = HarvestedSciELOData
    menu_label = "SciELO Data"
    menu_icon = "doc-full"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class HarvestedBooksAdmin(ModelAdmin):
    model = HarvestedBooks
    menu_label = "Books"
    menu_icon = "doc-full"
    list_display = ("identifier","type_data", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class TransformationScriptCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class TransformationScriptButtonHelper(ButtonHelper):
    """ButtonHelper para adicionar botão de executar transformação."""

    run_button_classnames = ["button-small", "button-secondary", "icon", "icon-download"]

    def run_transform_button(self, obj):
        text = _("Executar Transformação")
        return {
            "url": reverse("harvest_run_transform") + f"?script_id={obj.id}",
            "label": text,
            "classname": self.finalise_classname(self.run_button_classnames),
            "title": text,
        }

    def get_buttons_for_obj(self, obj, exclude=None, classnames_add=None, classnames_exclude=None):
        btns = super().get_buttons_for_obj(obj, exclude, classnames_add, classnames_exclude)
        if "run_transform" not in (exclude or []):
            btns.append(self.run_transform_button(obj))
        return btns


class TransformationScriptAdmin(ModelAdmin):
    model = TransformationScript
    menu_label = "Scripts de Transformação"
    menu_icon = "code"
    create_view_class = TransformationScriptCreateView
    button_helper_class = TransformationScriptButtonHelper
    list_display = ("name", "source_index", "dest_index", "is_active", "updated")
    search_fields = ("name", "description", "source_index", "dest_index")
    list_filter = ("is_active",)


class HarvestModelAdminGroup(ModelAdminGroup):
    menu_label = "Harvest"
    menu_icon = "download"
    items = (
        HarvestedPreprintAdmin,
        HarvestedSciELODataAdmin,
        HarvestedBooksAdmin,
        TransformationScriptAdmin
    )

modeladmin_register(HarvestModelAdminGroup)


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
    ]
