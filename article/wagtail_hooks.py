from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
    ModelAdminGroup,
)

from .models import (
    Article,
    SourceArticle,
    Contributor,
    Affiliation,
    Journal,
    License,
    Concepts
)


class SourceArticleAdmin(ModelAdmin):
    model = SourceArticle
    menu_label = _(
        "Source Articles"
    )  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "doi",
        "specific_id",
        "year",
        "is_paratext",
        "updated",
        "created",
    )

    list_filter = (
        "year",
        "is_paratext",
        "source",
    )
    search_fields = (
        "doi",
        "specific_id",
    )


class ConceptsAdmin(ModelAdmin):
    model = Concepts
    menu_label = _("Concepts")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_parents_id(self, obj):
        return " | ".join([str(c) for c in obj.parent_ids.all()])

    def all_theme(self, obj):
        return " | ".join([str(c) for c in obj.thematic_areas.all()])

    list_display = (
        "name",
        "specific_id",
        "normalized_name",
        "level",
        "parent_display_names",
        "all_parents_id",
        "all_theme",
    )

    list_filter = (
        "level",
        "thematic_areas",
    )
    search_fields = ("name", "specific_id", "normalized_name")


class ArticleAdmin(ModelAdmin):
    model = Article
    menu_label = _("Articles")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_contributors(self, obj):
        return " | ".join([str(c) for c in obj.contributors.all()])

    def all_theme(self, obj):
        themes = []
        for c in obj.concepts.all():
            themes.extend(
                ["%s (%s)" % (str(t), t.id) for t in c.thematic_areas.all() if t]
            )
        return " | ".join(themes)

    list_display = (
        "doi",
        "title",
        "journal",
        "volume",
        "number",
        "year",
        "open_access_status",
        "license",
        # "apc",
        "all_contributors",
        "all_theme",
    )

    list_filter = (
        "year",
        "license",
        "open_access_status",
        "apc",
        "is_oa",
    )
    search_fields = (
        "doi",
        "year",
    )


class JournalAdmin(ModelAdmin):
    model = Journal
    menu_label = _("Journals")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "journal_issn_l",
        "journal_issns",
        "journal_name",
        "publisher",
        "journal_is_in_doaj",
    )

    list_filter = ("journal_is_in_doaj",)
    search_fields = ("journal_issn_l", "journal_name", "journal_issns", "publisher")


class ContributorAdmin(ModelAdmin):
    model = Contributor
    menu_label = _("Contributors")
    menu_icon = "folder-open-inverse"
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_institutions(self, obj):
        return " | ".join(
            [str("%s(%s)" % (c.name, c.id)) for c in obj.institutions.all()]
        )

    def all_affiliations(self, obj):
        return " | ".join(
            [str("%s(%s)" % (c.name, c.id)) for c in obj.affiliations.all()]
        )

    list_display = (
        "family",
        "given",
        "orcid",
        "all_institutions",
        "all_affiliations",
        "authenticated_orcid",
    )

    # list_filter = ('orcid',)
    search_fields = ("orcid", "family", "given")


class AffiliationAdmin(ModelAdmin):
    model = Affiliation
    menu_label = _("Affiliations")
    menu_icon = "folder-open-inverse"
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("name", "official", "country", "source")
    # list_filter = ("country",)
    search_fields = ("name",)


class LicenseAdmin(ModelAdmin):
    model = License
    menu_label = _("Licenses")
    menu_icon = "folder-open-inverse"
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "name",
        "delay_in_days",
        "start",
        "url",
    )
    list_filter = ("name", "url")
    search_fields = ("name", "url")


class ArticleAdminGroup(ModelAdminGroup):
    menu_label = _("Article Directory")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        ArticleAdmin,
        JournalAdmin,
        ContributorAdmin,
        AffiliationAdmin,
        LicenseAdmin,
        ConceptsAdmin,
        SourceArticleAdmin,
    )


modeladmin_register(ArticleAdminGroup)
