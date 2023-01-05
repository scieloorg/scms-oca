from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register, ModelAdminGroup
from wagtail.contrib.modeladmin.views import CreateView

from .models import JournalArticle, Thesis, RawArticle, ConferenceProceedings
from .core import GenericArticle


class JournalArticleCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalArticleAdmin(ModelAdmin):
    model = JournalArticle
    inspect_view_enabled = True
    menu_label = _('Journal Article')
    create_view_class = JournalArticleCreateView
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False

    def journal_titles(self, obj):
        return " | ".join([str(c) for c in obj.journal_title.all()])

    def issns(self, obj):
        return " | ".join([str(c) for c in obj.issn.all()])

    def article_titles(self, obj):
        return " | ".join([str(c) for c in obj.document_title.all()])

    list_display = (
        'document_type',
        'article_titles',
        'journal_titles',
        'issns',
        'series',
    )
    list_filter = ()
    search_fields = (
        'journal_titles',
        'issns',
        'article_titles',
    )


class ConferenceProceedingsCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ConferenceProceedingsAdmin(ModelAdmin):
    model = ConferenceProceedings
    inspect_view_enabled = True
    menu_label = _('Conference Proceedings')
    create_view_class = ConferenceProceedingsCreateView
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    def document_titles(self, obj):
        return " | ".join([str(c) for c in obj.document_title.all()])

    def id_lattes_authors(self, obj):
        return " | ".join([str(c) for c in obj.authors.all()])

    list_display = (
        'document_type',
        'document_titles',
        'id_lattes_authors',
    )
    list_filter = ()
    search_fields = (
        'document_titles',
    )


class ThesisCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ThesisAdmin(ModelAdmin):
    model = Thesis
    inspect_view_enabled = True
    menu_label = _('Thesis')
    create_view_class = ThesisCreateView
    menu_icon = 'folder'
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    def document_titles(self, obj):
        return " | ".join([str(c) for c in obj.document_title.all()])

    def lattes_id_authors(self, obj):
        return " | ".join([str(c) for c in obj.authors.all()])

    list_display = (
        'document_type',
        'document_titles',
        'lattes_id_authors',
    )
    list_filter = ()
    search_fields = (
        'document_titles',
    )


class RawArticleView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class RawArticleAdmin(ModelAdmin):
    model = RawArticle
    inspect_view_enabled = True
    menu_label = _('Raw article')
    create_view_class = RawArticleView
    menu_icon = 'folder'
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        'document_type',
        'entity_id',
        'json',
    )
    # list_filter = ()
    # search_fields = (
    #     'official',
    # )


class ArticlesAdminGroup(ModelAdminGroup):
    menu_label = _('Articles IBICT')
    menu_icon = 'folder-open-inverse'  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (JournalArticleAdmin, ConferenceProceedingsAdmin, ThesisAdmin, RawArticleAdmin)


modeladmin_register(ArticlesAdminGroup)
