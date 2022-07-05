from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import EducationDirectory, EducationDirectoryFile
from .button_helper import EducationDirectoryHelper
from .views import validate, import_file


class EducationDirectoryCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class EducationDirectoryFileCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class EducationDirectoryAdmin(ModelAdmin):
    model = EducationDirectory
    create_view_class = EducationDirectoryCreateView
    menu_label = _('Education Directory')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('title', 'link', 'description', 'creator',
                    'updated', 'created')
    search_fields = ('title', 'description')
    list_export = ('title', 'link', 'description')
    export_filename = 'education_directory'


class EducationDirectoryFileAdmin(ModelAdmin):
    model = EducationDirectoryFile
    create_view_class=EducationDirectoryFileCreateView
    button_helper_class = EducationDirectoryHelper
    menu_label = _('Education Directory Upload')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('attachment', 'line_count', 'is_valid', 'creator',
                    'updated', 'created', )
    list_filter = ('is_valid', )
    search_fields = ('attachment', )


class EducationDirectoryAdminGroup(ModelAdminGroup):
    menu_label = _('Education Directory')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (EducationDirectoryAdmin, EducationDirectoryFileAdmin,)


modeladmin_register(EducationDirectoryAdminGroup)


@hooks.register('register_admin_urls')
def register_education_url():
    return [
        path('education_directory/educationdirectoryfile/',
        include('education_directory.urls', namespace='education_directory')),
    ]
