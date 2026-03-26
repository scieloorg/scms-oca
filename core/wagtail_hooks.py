"""File: core/wagtail_hooks.py."""

from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail_modeladmin.options import ModelAdmin, modeladmin_register

from core.models import SAMenu, Source


@hooks.register("insert_global_admin_css", order=100)
def global_admin_css():
    """Add /static/admin/css/custom.css to the admin."""
    return format_html(
        '<link rel="stylesheet" href="{}">', static("admin/css/custom.css")
    )


@hooks.register("insert_global_admin_js", order=100)
def global_admin_js():
    """Add /static/admin/css/custom.js to the admin."""
    return format_html('<script src="{}"></script>', static("admin/js/custom.js"))



class SourceAdmin(ModelAdmin):
    model = Source
    menu_label = _("Sources")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = ("name",)

    list_filter = ("name",)
    search_fields = ("name", )



modeladmin_register(SourceAdmin)


class SAMenuSnippetViewSet(SnippetViewSet):
    model = SAMenu
    icon = "list-ul"
    menu_label = _("SciELO Analytics Menus")
    add_to_admin_menu = True
    menu_order = 250
    list_display = ("title", "handle", "locale", "is_active")
    list_filter = ("is_active", "locale")
    search_fields = ("title", "handle", "short_name")


register_snippet(SAMenuSnippetViewSet)
