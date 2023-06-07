from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
    ModelAdminGroup,
)

from .models import (
    ScholarlyArticles,
    Contributors,
    Affiliations,
    Journals,
    RawUnpaywall,
    SupplementaryData,
    ErrorLog,
    License,
    Programs,
)


class ScholarlyArticlesAdmin(ModelAdmin):
    model = ScholarlyArticles
    menu_label = _(
        "Scholarly Articles"
    )  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    # menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_contributors(self, obj):
        return " | ".join([str(c) for c in obj.contributors.all()])

    list_display = (
        "doi",
        "title",
        "volume",
        "number",
        "year",
        "open_access_status",
        "use_license",
        "license",
        "apc",
        "all_contributors",
        "journal",
        "source",
    )

    list_filter = ("source", "year")
    search_fields = ("doi",)


class RawUnpaywallAdmin(ModelAdmin):
    model = RawUnpaywall
    menu_label = _("RawUnpaywall")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    # menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "doi",
        "harvesting_creation",
        "is_paratext",
        "year",
        "resource_type",
        "update",
        "json",
    )

    list_filter = ("year",)
    search_fields = ("doi",)


class JournalsAdmin(ModelAdmin):
    model = Journals
    menu_label = _("Journals")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    # menu_order = 000  # will put in 3rd place (000 being 1st, 100 2nd)
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


class ContributorsAdmin(ModelAdmin):
    model = Contributors
    menu_label = _("Contributors")
    menu_icon = "folder-open-inverse"
    # menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "family",
        "given",
        "orcid",
        "authenticated_orcid",
        "affiliation",
    )

    # list_filter = ('orcid',)
    search_fields = (
        "orcid",
        "family",
        "given"
    )


class AffiliationsAdmin(ModelAdmin):
    model = Affiliations
    menu_label = _("Affiliations")
    menu_icon = "folder-open-inverse"
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "name",
        "official",
        "country",
    )
    list_filter = ("country",)
    search_fields = (
        "name",
    )


class SupplementaryDataAdmin(ModelAdmin):
    model = SupplementaryData
    menu_label = _("Supplementary Data")
    menu_icon = "folder-open-inverse"
    inspect_view_enabled = True
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "doi",
        "year",
    )
    # list_filter = ('name',)
    search_fields = ("doi",)


class ErrorLogAdmin(ModelAdmin):
    model = ErrorLog
    menu_label = _("Errors")
    menu_icon = "folder-open-inverse"
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "created",
        "error_type",
        "error_message",
    )
    list_filter = ("error_type",)
    search_fields = ("document_id",)


class LicenseAdmin(ModelAdmin):
    model = License
    menu_label = _("License")
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

class ProgramsAdmin(ModelAdmin):
    model = Programs
    menu_label = _("Programs")
    menu_icon = "folder-open-inverse"
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "name",
        "institution",
    )
    list_filter = ("name",)
    search_fields = ("name", "institution")


class ScholarlyArticlesAdminGroup(ModelAdminGroup):
    menu_label = _("Articles Directory")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        JournalsAdmin,
        ScholarlyArticlesAdmin,
        ContributorsAdmin,
        AffiliationsAdmin,
        ProgramsAdmin,
        RawUnpaywallAdmin,
        SupplementaryDataAdmin,
        LicenseAdmin,
        ErrorLogAdmin,
    )


modeladmin_register(ScholarlyArticlesAdminGroup)
