from django.urls import include, path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)

from . import views
from .button_helper import InfrastructureDirectoryHelper
from .models import InfrastructureDirectory, InfrastructureDirectoryFile


class InfrastructureDirectoryAdmin(ModelAdmin):
    model = InfrastructureDirectory
    ordering = ("-updated",)
    create_view_class = views.InfrastructureDirectoryCreateView
    edit_view_class = views.InfrastructureDirectoryEditView
    menu_label = _("Infraestructure Directory")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("title", "link", "record_status", "description", "creator", "updated", "created")
    list_filter = ("practice", "classification", "thematic_areas", "record_status")
    search_fields = ("title", "description")
    list_export = ("title", "link", "description")
    export_filename = "infra_directory"

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # If the user is not a staff
        if not request.user.is_staff:
            # Only show the records create by the current user
            return qs.filter(creator=request.user)
        else: 
            return qs


class InfrastructureDirectoryFileAdmin(ModelAdmin):
    model = InfrastructureDirectoryFile
    ordering = ("-updated",)
    create_view_class = views.InfrastructureDirectoryFileCreateView
    button_helper_class = InfrastructureDirectoryHelper
    menu_label = _("Infraestructure Directory Upload")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "attachment",
        "line_count",
        "is_valid",
        "creator",
        "updated",
        "created",
    )
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


class InfrastructureDirectoryAdminGroup(ModelAdminGroup):
    menu_label = _("Infraestructure Directory")
    menu_icon = "folder-open-inverse"
    menu_order = 200
    items = (
        InfrastructureDirectoryAdmin,
        InfrastructureDirectoryFileAdmin,
    )


modeladmin_register(InfrastructureDirectoryAdminGroup)


@hooks.register("register_admin_urls")
def register_calendar_url():
    return [
        path(
            "infrastructure_directory/infrastructuredirectoryfile/",
            include(
                "infrastructure_directory.urls", namespace="infrastructure_directory"
            ),
        ),
    ]
