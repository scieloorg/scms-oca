from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import DataSource, SettingsFilter


class DataSourceSnippetViewSet(SnippetViewSet):
    model = DataSource
    icon = "search"
    menu_label = _("Data Sources")
    list_display = ("index_name", "display_name")
    search_fields = ("index_name", "display_name")

register_snippet(DataSourceSnippetViewSet)
