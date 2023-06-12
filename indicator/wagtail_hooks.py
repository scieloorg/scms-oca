from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
)

from . import views
from .models import Indicator


class IndicatorAdmin(ModelAdmin):
    model = Indicator
    ordering = ("-updated",)
    create_view_class = views.IndicatorDirectoryCreateView
    edit_view_class = views.IndicatorDirectoryEditView
    menu_label = _("Indicator")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    inspect_view_enabled = True

    list_display = (
        "title",
        "record_status",
        "institutional_contribution",
        "validity",
        "updated",
    )

    list_filter = (
        "action_and_practice__action__name",
        "action_and_practice__classification",
        "action_and_practice__practice__name",
        "record_status",
        "validity",
        "scope",
        "measurement",
        "object_name",
        "category",
        "context",
        "institutional_contribution",
    )

    search_fields = (
        "slug",
        "title",
        "institutional_contribution",
        "action_and_practice__action__name",
        "action_and_practice__classification",
        "action_and_practice__practice__name",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # If the user is not a staff
        if not request.user.is_staff:
            # Only show the records create by the current user
            return qs.filter(creator=request.user)
        else:
            return qs


modeladmin_register(IndicatorAdmin)
