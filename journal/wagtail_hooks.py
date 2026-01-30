from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import ModelAdmin

from .models import SourceJournal


class SourceJournalAdmin(ModelAdmin):
    model = SourceJournal
    menu_label = _(
        "Source Journals"
    )  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "issns",
        "title",
        "specific_id",
        "updated",
        "created",
    )

    list_filter = (
        "source",
        "country_code",
    )
    search_fields = (
        "title"
        "issns",
        "specific_id",
    )