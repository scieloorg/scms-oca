from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import (ScholarlyArticle, Contributor, Affiliation, Journal, RawRecord, ErrorLog)


class ScholarlyArticleAdmin(ModelAdmin):
    model = ScholarlyArticle
    menu_label = _('Scholarly Articles')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    #menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    inspect_view_enabled = True

    def all_contributors(self, obj):
        return " | ".join([str(c) for c in obj.contributors.all()])

    def all_sources(self, obj):
        return " | ".join([str(s) for s in obj.sources.all()])

    list_display = (
        'doi',
        'title',
        'year',
        'all_contributors',
        'journal',
        'all_sources',
    )

    list_filter = ('year',)
    search_fields = ('doi',)


class RawRecordAdmin(ModelAdmin):
    model = RawRecord
    menu_label = _('Raw Record')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    #menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    inspect_view_enabled = True

    list_display = (
        'doi',
        'harvesting_creation',
        'year',
        'resource_type',
        'source',
    )

    list_filter = ('year',)
    search_fields = ('doi',)


class JournalAdmin(ModelAdmin):
    model = Journal
    menu_label = _('Journals')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    #menu_order = 000  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    def all_sources(self, obj):
        return " | ".join([str(s) for s in obj.sources.all()])

    list_display = (
        'journal_issn_l',
        'journal_issns',
        'journal_name',
        'publisher',
        'journal_is_in_doaj',
        'all_sources',
    )

    #list_filter = (_('journal_issn_l'),)
    search_fields = (_('journal_issn_l)'),)


class ContributorAdmin(ModelAdmin):
    model = Contributor
    menu_label = _('Contributors')
    menu_icon = 'folder-open-inverse'
    #menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    def all_affiliations(self, obj):
        return " | ".join([str(c) for c in obj.affiliation.all()])

    def all_sources(self, obj):
        return " | ".join([str(s) for s in obj.sources.all()])

    list_display = (
        'family',
        'given',
        'orcid',
        'authenticated_orcid',
        'all_affiliations',
        'all_sources',
    )

    # list_filter = ('orcid',)
    search_fields = ('orcid', 'family', 'given', 'affiliation',)


class AffiliationAdmin(ModelAdmin):
    model = Affiliation
    menu_label = _('Affiliations')
    menu_icon = 'folder-open-inverse'
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    def all_sources(self, obj):
        return " | ".join([str(s) for s in obj.sources.all()])

    list_display = (
        'name',
        'official',
        'all_sources',
    )
    #list_filter = ('name',)
    search_fields = ('name', 'official',)


class ErrorLogAdmin(ModelAdmin):
    model = ErrorLog
    menu_label = _('Errors')
    menu_icon = 'folder-open-inverse'
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = (
        'created',
        'error_type',
        'error_message',
    )
    list_filter = ('error_type',)
    search_fields = ('document_id',)


class ScholarlyArticleAdminGroup(ModelAdminGroup):
    menu_label = _('Articles Directory')
    menu_icon = 'folder-open-inverse'  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (JournalAdmin,
             ScholarlyArticleAdmin,
             ContributorAdmin,
             AffiliationAdmin,
             RawRecordAdmin,
             ErrorLogAdmin)


modeladmin_register(ScholarlyArticleAdminGroup)
