from django.utils.translation import gettext_lazy as _

CITATION_EXPORT_FORMATS = {
    "bib": _("BibTeX"),
    "ris": _("Reference Manager"),
    "csv": _("CSV"),
}

CITATION_PRESET_STYLES = {
    "vancouver": _("Vancouver"),
    "apa": _("American Psychological Association"),
}
