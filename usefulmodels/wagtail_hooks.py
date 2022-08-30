from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import City, State, Country, ThematicArea, Practice, Action


class CityCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class StateCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class CountryCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

class ThematicAreaCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

class PracticeCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

class ActionCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class CityAdmin(ModelAdmin):
    model = City
    create_view_class = CityCreateView
    menu_label = _('City')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('name', 'creator',
                    'updated', 'created')
    search_fields = ('name', )
    list_export = ('name',)
    export_filename = 'cities'


class StateAdmin(ModelAdmin):
    model = State
    create_view_class = StateCreateView
    menu_label = _('State')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('name', 'acronym', 'region', 'creator',
                    'updated', 'created',)
    search_fields = ('name', 'acronym',)
    list_export = ('name', 'acronym', 'region',)
    export_filename = 'states'


class CountryAdmin(ModelAdmin):
    model = Country
    create_view_class = CountryCreateView
    menu_label = _('Country')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('name', 'acronym', 'creator',
                    'updated', 'created')
    search_fields = ('name', 'acronym')
    list_export = ('name', 'acronym')
    export_filename = 'countryies'


class ThematicAreaAdmin(ModelAdmin):
    model = ThematicArea
    create_view_class = ThematicAreaCreateView
    menu_label = _('Thematic Area')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('level0', 'level1', 'level2', 'creator',
                    'updated', 'created', )
    search_fields = ('level0', 'level1', 'level2', )
    list_export = ('level0', 'level1', 'level2', 'creator',
                   'updated', 'created', )
    export_filename = 'thematic_areas'

class PracticeAdmin(ModelAdmin):
    model = Practice
    create_view_class = PracticeCreateView
    menu_label = _('Practice')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('name', 'code', 'creator',
                    'updated', 'created', )
    search_fields = ('name', 'code',)
    list_export = ('name', 'code', 'creator',
                   'updated', 'created', )
    export_filename = 'pratices'

class ActionAdmin(ModelAdmin):
    model = Action
    create_view_class = ActionCreateView
    menu_label = _('Action')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('name', 'code', 'creator',
                    'updated', 'created', )
    search_fields = ('name', 'code',)
    list_export = ('name', 'code', 'creator',
                   'updated', 'created', )
    export_filename = 'actions'


class UsefulModelsAdminGroup(ModelAdminGroup):
    menu_label = _('Useful Models')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (CityAdmin, StateAdmin, CountryAdmin, PracticeAdmin, ActionAdmin,
             ThematicAreaAdmin)


modeladmin_register(UsefulModelsAdminGroup)
