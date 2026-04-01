from django.utils.translation import gettext as _
from wagtail_modeladmin.options import ModelAdmin, modeladmin_register

from .models import ObservationPage


class ObservationPageAdmin(ModelAdmin):
    model = ObservationPage
    menu_label = _("Observation")
    menu_icon = "view"
    menu_order = 320
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("title", "data_source", "live", "latest_revision_created_at")
    search_fields = ("title", "data_source__display_name", "data_source__index_name")


modeladmin_register(ObservationPageAdmin)
