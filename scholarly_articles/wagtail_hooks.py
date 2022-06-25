from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register)

from .models import (ScholarlyArticles, Contributor)


class ScholarlyArticlesAdmin(ModelAdmin):
    model = ScholarlyArticles
    menu_label = 'Scholarly Articles'  # ditch this to use verbose_name_plural from model
    menu_icon = 'folder'  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = (
        'doi',
        'doi_url',
        'genre',
        'is_oa',
        'journal_is_in_doaj',
        'journal_issns',
        'journal_issn_l',
        'journal_name',
        'published_date',
        'publisher',
        'title',
    )
    # list_filter = ('source_type',)
    # search_fields = ('name', 'source_type')


