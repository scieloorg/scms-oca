from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import DisclosureDirectory, DisclosureDirectoryFile
from .button_helper import DisclosureDirectoryHelper
from .views import validate, import_file


class DisclosureDirectoryCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class DisclosureDirectoryFileCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class DisclosureDirectoryAdmin(ModelAdmin):
    model = DisclosureDirectory
    create_view_class = DisclosureDirectoryCreateView
    menu_label = _('Disclosure Directory')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('event', 'link', 'description', 'creator',
                    'updated', 'created')
    search_fields = ('event', 'description')
    list_export = ('event', 'link', 'description')
    export_filename = 'disclosure_directory'


class DisclosureDirectoryFileAdmin(ModelAdmin):
    model = DisclosureDirectoryFile
    create_view_class=DisclosureDirectoryFileCreateView
    button_helper_class = DisclosureDirectoryHelper
    menu_label = _('Disclosure Directory Upload')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('attachment', 'line_count', 'is_valid', 'creator',
                    'updated', 'created', )
    list_filter = ('is_valid', )
    search_fields = ('attachment', )


class DisclosureDirectoryAdminGroup(ModelAdminGroup):
    menu_label = _('Disclosure Directory')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (DisclosureDirectoryAdmin, DisclosureDirectoryFileAdmin,)


modeladmin_register(DisclosureDirectoryAdminGroup)


@hooks.register('register_admin_urls')
def register_disclosure_url():
    return [
        path('disclosure_directory/DisclosureDirectoryfile/',
        include('disclosure_directory.urls', namespace='disclosure_directory')),
    ]
