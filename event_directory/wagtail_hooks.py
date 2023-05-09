from django.urls import include, path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)

from . import views
from .button_helper import EventDirectoryHelper
from .models import EventDirectory, EventDirectoryFile


class EventDirectoryAdmin(ModelAdmin):
    model = EventDirectory
    ordering = ("-updated",)
    create_view_class = views.EventDirectoryCreateView
    edit_view_class = views.EventDirectoryEditView
    menu_label = _("Event Directory")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "title",
        "link",
        "record_status",
        "description",
        "institutional_contribution",
        "creator",
        "updated",
        "created",
    )
    list_filter = (
        "practice",
        "classification",
        "thematic_areas",
        "record_status",
        "institutional_contribution",
    )
    search_fields = ("title", "description")
    list_export = ("title", "link", "description")
    export_filename = "event_directory"

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # If the user is not a staff
        if not request.user.is_staff:
            # Only show the records create by the current user
            return qs.filter(creator=request.user)
        else:
            return qs


class EventDirectoryFileAdmin(ModelAdmin):
    model = EventDirectoryFile
    ordering = ("-updated",)
    create_view_class = views.EventDirectoryFileCreateView
    button_helper_class = EventDirectoryHelper
    menu_label = _("Event Directory Upload")
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


class EventDirectoryAdminGroup(ModelAdminGroup):
    menu_label = _("Event Directory")
    menu_icon = "folder-open-inverse"
    menu_order = 200
    items = (
        EventDirectoryAdmin,
        EventDirectoryFileAdmin,
    )


modeladmin_register(EventDirectoryAdminGroup)


@hooks.register("register_admin_urls")
def register_Event_url():
    return [
        path(
            "event_directory/eventDirectoryfile/",
            include("event_directory.urls", namespace="event_directory"),
        ),
    ]
