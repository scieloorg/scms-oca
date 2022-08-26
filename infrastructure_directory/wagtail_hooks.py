from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView, EditView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import InfrastructureDirectory, InfrastructureDirectoryFile
from .button_helper import InfrastructureDirectoryHelper

from usefulmodels.models import Action


class InfrastructureDirectoryCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_instance(self):

        instance = super().get_instance()

        if Action.objects.filter(name__icontains="infraestrutura").exists():
            instance.practice = Action.objects.get(name__icontains="infraestrutura")

        return instance

class InfrastructureDirectoryEditView(EditView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class InfrastructureDirectoryFileCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class InfrastructureDirectoryAdmin(ModelAdmin):
    model = InfrastructureDirectory
    ordering = ('-updated',)
    create_view_class = InfrastructureDirectoryCreateView
    edit_view_class = InfrastructureDirectoryEditView
    menu_label = _('Infraestructure Directory')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('title', 'link', 'description', 'creator',
                    'updated', 'created')
    search_fields = ('title', 'description')
    list_export = ('title', 'link', 'description')
    export_filename = 'infra_directory'


class InfrastructureDirectoryFileAdmin(ModelAdmin):
    model = InfrastructureDirectoryFile
    ordering = ('-updated',)
    create_view_class=InfrastructureDirectoryFileCreateView
    button_helper_class = InfrastructureDirectoryHelper
    menu_label = _('Infraestructure Directory Upload')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('attachment', 'line_count', 'is_valid', 'creator',
                    'updated', 'created', )
    list_filter = ('is_valid', )
    search_fields = ('attachment', )


class InfrastructureDirectoryAdminGroup(ModelAdminGroup):
    menu_label = _('Infraestructure Directory')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (InfrastructureDirectoryAdmin, InfrastructureDirectoryFileAdmin,)


modeladmin_register(InfrastructureDirectoryAdminGroup)


@hooks.register('register_admin_urls')
def register_calendar_url():
    return [
        path('infrastructure_directory/infrastructuredirectoryfile/',
        include('infrastructure_directory.urls', namespace='infrastructure_directory')),

    ]
