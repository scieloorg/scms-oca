from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import (ScholarlyArticles, Contributors, Affiliations, Journals, RawUnpaywall, ErrorLog)


class ScholarlyArticlesAdmin(ModelAdmin):
    model = ScholarlyArticles
    menu_label = _('Scholarly Articles')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    #menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    def all_contributors(self, obj):
        return " | ".join([str(c) for c in obj.contributors.all()])

    list_display = (
        'doi',
        'year',
        'all_contributors',
        'journal',
    )

    list_filter = ('year',)
    search_fields = ('doi',)


class RawUnpaywallAdmin(ModelAdmin):
    model = RawUnpaywall
    menu_label = _('RawUnpaywall')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    #menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    list_display = (
        'doi',
        'harvesting_creation',
        'is_paratext',
        'year',
        'resource_type',
        'update',
        'json',
    )

    list_filter = ('year',)
    search_fields = ('doi',)


class JournalsAdmin(ModelAdmin):
    model = Journals
    menu_label = _('Journals')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    #menu_order = 000  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    list_display = (
        'journal_issn_l',
        'journal_issns',
        'journal_name',
        'publisher',
        'journal_is_in_doaj',
    )

    #list_filter = (_('journal_issn_l'),)
    search_fields = (_('journal_issn_l)'),)


class ContributorsAdmin(ModelAdmin):
    model = Contributors
    menu_label = _('Contributors')
    menu_icon = 'folder-open-inverse'
    #menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    list_display = (
        'family',
        'given',
        'orcid',
        'authenticated_orcid',
        'affiliation',
    )

    # list_filter = ('orcid',)
    search_fields = ('orcid', 'family', 'given', 'affiliation',)


class AffiliationsAdmin(ModelAdmin):
    model = Affiliations
    menu_label = _('Affiliations')
    menu_icon = 'folder-open-inverse'
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = (
        'name',
    )
    #list_filter = ('name',)
    search_fields = ('name',)


class ErrorLogAdmin(ModelAdmin):
    model = ErrorLog
    menu_label = _('Errors')
    menu_icon = 'folder-open-inverse'
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = (
        'created',
        'document_id',
        'error_type',
        'error_message',
    )
    list_filter = ('error_type',)
    search_fields = ('document_id',)


class ScholarlyArticlesAdminGroup(ModelAdminGroup):
    menu_label = _('Articles Directory')
    menu_icon = 'folder-open-inverse'  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (JournalsAdmin, ScholarlyArticlesAdmin, ContributorsAdmin, AffiliationsAdmin, RawUnpaywallAdmin, ErrorLogAdmin)


modeladmin_register(ScholarlyArticlesAdminGroup)
