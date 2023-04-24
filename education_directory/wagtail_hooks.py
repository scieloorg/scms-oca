from django.urls import include, path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)

from . import views
from .button_helper import EducationDirectoryHelper
from .models import EducationDirectory, EducationDirectoryFile


class EducationDirectoryAdmin(ModelAdmin):
    model = EducationDirectory
    ordering = ("-updated",)
    create_view_class = views.EducationDirectoryCreateView
    # edit_view_class = EducationDirectoryEditView
    menu_label = _("Education Directory")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("title", "link", "description", "creator", "updated", "created")
    list_filter = ("practice", "classification", "thematic_areas", "record_status")
    search_fields = ("title", "description")
    list_export = ("title", "link", "description")
    export_filename = "education_directory"


class EducationDirectoryFileAdmin(ModelAdmin):
    model = EducationDirectoryFile
    ordering = ("-updated",)
    create_view_class = views.EducationDirectoryFileCreateView
    button_helper_class = EducationDirectoryHelper
    menu_label = _("Education Directory Upload")
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


class EducationDirectoryAdminGroup(ModelAdminGroup):
    menu_label = _("Education Directory")
    menu_icon = "folder-open-inverse"
    menu_order = 200
    items = (
        EducationDirectoryAdmin,
        EducationDirectoryFileAdmin,
    )


modeladmin_register(EducationDirectoryAdminGroup)


@hooks.register("register_admin_urls")
def register_education_url():
    return [
        path(
            "education_directory/educationdirectoryfile/",
            include("education_directory.urls", namespace="education_directory"),
        ),
    ]
