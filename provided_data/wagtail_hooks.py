from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail_modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail_modeladmin.views import CreateView

from .models import JournalArticle, Thesis, RawArticle, ConferenceProceedings
from .core import Authorship


class JournalArticleCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalArticleAdmin(ModelAdmin):
    model = JournalArticle
    inspect_view_enabled = True
    menu_label = _("Journal Article")
    create_view_class = JournalArticleCreateView
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False

    def periodical_titles(self, obj):
        return " | ".join([str(c) for c in obj.journal_titles.all()])

    def all_issn(self, obj):
        return " | ".join([str(c) for c in obj.issns.all()])

    def article_titles(self, obj):
        return " | ".join([str(c) for c in obj.document_titles.all()])

    def article_keywords(self, obj):
        return " | ".join([str(c) for c in obj.keywords.all()])

    list_display = (
        "document_type",
        "article_titles",
        "periodical_titles",
        "all_issn",
        "series",
        "article_keywords",
    )
    list_filter = ()
    search_fields = (
        "periodical_titles",
        "all_issn",
        "article_titles",
    )


class ConferenceProceedingsCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ConferenceProceedingsAdmin(ModelAdmin):
    model = ConferenceProceedings
    inspect_view_enabled = True
    menu_label = _("Conference Proceedings")
    create_view_class = ConferenceProceedingsCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    def conference_titles(self, obj):
        return " | ".join([str(c) for c in obj.document_titles.all()])

    def id_lattes_authors(self, obj):
        return " | ".join([str(c) for c in obj.authors.all()])

    list_display = (
        "document_type",
        "conference_titles",
        "id_lattes_authors",
    )
    list_filter = ()
    search_fields = ("conference_titles",)


class ThesisCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ThesisAdmin(ModelAdmin):
    model = Thesis
    inspect_view_enabled = True
    menu_label = _("Thesis")
    create_view_class = ThesisCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    def thesis_titles(self, obj):
        return " | ".join([str(c) for c in obj.document_titles.all()])

    def id_lattes_authors(self, obj):
        return " | ".join([str(c) for c in obj.authors.all()])

    list_display = (
        "document_type",
        "thesis_titles",
        "id_lattes_authors",
    )
    list_filter = ()
    search_fields = ("thesis_titles",)


class AuthorshipCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class AuthorshipAdmin(ModelAdmin):
    model = Authorship
    inspect_view_enabled = True
    menu_label = _("Persons")
    create_view_class = AuthorshipCreateView
    menu_icon = "folder"
    menu_order = 400
    add_to_settings_menu = False
    exclude_from_explorer = False

    def all_names(self, obj):
        return " | ".join([str(c) for c in obj.names.all()])

    def areas(self, obj):
        return " | ".join([str(c) for c in obj.person_research_areas.all()])

    list_display = (
        "all_names",
        "areas",
        "birth_city",
        "birth_state",
        "birth_country",
    )
    list_filter = ()
    search_fields = ("all_names",)


class RawArticleView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class RawArticleAdmin(ModelAdmin):
    model = RawArticle
    inspect_view_enabled = True
    menu_label = _("Raw article")
    create_view_class = RawArticleView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "document_type",
        "entity_id",
        "json",
    )
    # list_filter = ()
    # search_fields = (
    #     'official',
    # )


class ArticlesAdminGroup(ModelAdminGroup):
    menu_label = _("Provided data")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        JournalArticleAdmin,
        ConferenceProceedingsAdmin,
        ThesisAdmin,
        AuthorshipAdmin,
        RawArticleAdmin,
    )


modeladmin_register(ArticlesAdminGroup)
