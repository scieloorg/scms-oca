from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView, EditView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import (Indicator,)

class IndicatorDirectoryEditView(EditView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IndicatorDirectoryCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IndicatorAdmin(ModelAdmin):
    model = Indicator
    ordering = ('-updated',)
    create_view_class = IndicatorDirectoryCreateView
    edit_view_class = IndicatorDirectoryEditView
    menu_label = _('Indicator')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    list_display = (
        'title',
        'record_status',
        'updated',
    )

    list_filter = (
        'action',
        'practice',
        )

    search_fields = (
        'title',
        'description',
        'versioning',
        'action',
        'classification',
        'practice',
        'thematic_areas',
        'institutions',
        'locations',
        'start_date',
        'end_date',
        'record_status',
        'source',
    )


modeladmin_register(IndicatorAdmin)


@hooks.register('register_admin_urls')
def register_disclosure_url():
    return [
        path('indicator/',
        include('indicator.urls', namespace='indicator')),
    ]
