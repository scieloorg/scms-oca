from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import Institution, SourceInstitution


class InstitutionCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class InstitutionAdmin(ModelAdmin):
    model = Institution
    create_view_class = InstitutionCreateView
    menu_label = _("Institution")
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("name", "acronym", "location", "source", "updated")
    search_fields = ("name", "institution_type", "source")
    list_filter = ("institution_type", "source")
    list_export = (
        "name",
        "institution_type",
        "level_1",
        "level_2",
        "level_3",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    export_filename = "institutions"


class SourceInstitutionAdmin(ModelAdmin):
    model = SourceInstitution
    menu_label = _("Source Institution")
    menu_icon = "folder-open-inverse"
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_name(self, obj):
        return " | ".join([str(c.name) for c in obj.source_institution.all()])
    
    list_display = (
        "specific_id",
        "display_name",
        "all_name",
        "type",
        "country_code",
    )
    list_filter = ("type", "country_code")
    search_fields = ("display_name", "specific_id")

class InstitutionAdminGroup(ModelAdminGroup):
    menu_label = _("Instutition")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        InstitutionAdmin,
        SourceInstitutionAdmin,
    )

modeladmin_register(InstitutionAdminGroup)

