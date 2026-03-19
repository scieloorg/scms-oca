from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import DataSource


class DataSourceSnippetViewSet(SnippetViewSet):
    model = DataSource
    icon = "search"
    menu_label = _("Data Sources")
    list_display = ("index_name", "display_name")
    search_fields = ("index_name", "display_name")

register_snippet(DataSourceSnippetViewSet)



@hooks.register('insert_global_admin_css')
def global_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static('css/admin_custom.css')
    )
