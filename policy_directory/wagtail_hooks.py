from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView, EditView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import PolicyDirectory, PolicyDirectoryFile
from .button_helper import PolicyDirectoryHelper

from usefulmodels.models import Practice

class PolicyDirectoryEditView(EditView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PolicyDirectoryCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_instance(self):

        instance = super().get_instance()

        if Practice.objects.filter(name__icontains="política, recomendação etc.").exists():
            instance.practice = Practice.objects.get(name__icontains="política, recomendação etc.")

        return instance


class PolicyDirectoryFileCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PolicyDirectoryAdmin(ModelAdmin):
    model = PolicyDirectory
    ordering = ('-updated',)
    create_view_class = PolicyDirectoryCreateView
    edit_view_class = PolicyDirectoryEditView
    menu_label = _('Policy Directory')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('title', 'link', 'description', 'creator',
                    'updated', 'created')
    search_fields = ('title', 'description')
    list_export = ('title', 'link', 'description')
    export_filename = 'policy_directory'


class PolicyDirectoryFileAdmin(ModelAdmin):
    model = PolicyDirectoryFile
    ordering = ('-updated',)
    create_view_class=PolicyDirectoryFileCreateView
    button_helper_class = PolicyDirectoryHelper
    menu_label = _('Policy Directory Upload')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('attachment', 'line_count', 'is_valid', 'creator',
                    'updated', 'created', )
    list_filter = ('is_valid', )
    search_fields = ('attachment', )


class PolicyDirectoryAdminGroup(ModelAdminGroup):
    menu_label = _('Policy Directory')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (PolicyDirectoryAdmin, PolicyDirectoryFileAdmin,)


modeladmin_register(PolicyDirectoryAdminGroup)


@hooks.register('register_admin_urls')
def register_policy_url():
    return [
        path('policy_directory/PolicyDirectoryfile/',
        include('policy_directory.urls', namespace='policy_directory')),
    ]
