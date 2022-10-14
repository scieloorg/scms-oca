from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import (Articles, Contributors, Affiliations, Journals)


class ArticlesAdmin(ModelAdmin):
    model = Articles
    menu_label = _('Articles')  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder-open-inverse'  # change as required
    #menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    inspect_view_enabled = True

    def all_contributors(self, obj):
        return " | ".join([str(c) for c in obj.contributors.all()]) if obj.contributors is not None else ""

    list_display = (
        'doi',
        'title',
        'volume',
        'number',
        'year',
        'open_access_status',
        'use_license',
        'apc',
        'all_contributors',
        'journal',
        'source',
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

    def all_affiliations(self, obj):
        return " | ".join([str(c) for c in obj.affiliation.all()]) if obj.affiliation is not None else ""

    list_display = (
        'family',
        'given',
        'orcid',
        'authenticated_orcid',
        'all_affiliations',
    )

    # list_filter = ('orcid',)
    search_fields = ('orcid',)


class AffiliationsAdmin(ModelAdmin):
    model = Affiliations
    menu_label = _('Affiliations')
    menu_icon = 'folder-open-inverse'
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view

    list_display = (
        'name',
        'official',
        'source',
    )
    #list_filter = ('name',)
    search_fields = ('name',)


class ArticlesAdminGroup(ModelAdminGroup):
    menu_label = _('Articles Directory')
    menu_icon = 'folder-open-inverse'  # change as required
    menu_order = 500  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        ArticlesAdmin,
        JournalsAdmin,
        ContributorsAdmin,
        AffiliationsAdmin,
    )


modeladmin_register(ArticlesAdminGroup)
