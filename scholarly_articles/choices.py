from django.utils.translation import gettext as _

TYPE_OF_RESOURCE = [
    ("", ""),
    ("book-section", _("Book Section")),
    ("monograph", _("Monograph")),
    ("report", _("Report")),
    ("peer-review", _("Peer Review")),
    ("book-track", _("Book Track")),
    ("journal-article", _("Journal Article")),
    ("book-part", _("Part")),
    ("other", _("Other")),
    ("book", _("Book")),
    ("journal-volume", _("Journal Volume")),
    ("book-set", _("Book Set")),
    ("reference-entry", _("Reference Entry")),
    ("proceedings-article", _("Proceedings Article")),
    ("journal", _("Journal")),
    ("component", _("Component")),
    ("book-chapter", _("Book Chapter")),
    ("proceedings-series", _("Proceedings Series")),
    ("report-series", _("Report Series")),
    ("proceedings", _("Proceedings")),
    ("standard", _("Standard")),
    ("reference-book", _("Reference Book")),
    ("posted-content", _("Posted Content")),
    ("journal-issue", _("Journal Issue")),
    ("dissertation", _("Dissertation")),
    ("grant", _("Grant")),
    ("dataset", _("Dataset")),
    ("book-series", _("Book Series")),
    ("edited-book", _("Edited Book")),
    ("standard-series", _("Standard Series"))
]

OA_STATUS = [
    ("", ""),
    ("gold", _("Gold")),
    ("hybrid", _("Hybrid")),
    ("bronze", _("Bronze")),
    ("green", _("Green")),
    ("closed", _("Closed")),
]

LICENSE = [
    ("", ""),
    ("CC0", "CC0"),
    ("CC-BY", "CC-BY"),
    ("CC-BYNC", "CC-BYNC"),
    ("CC-BYND", "CC-BYND"),
    ("CC-BYNCND", "CC-BYNCND"),
]

APC = [
    ("", ""),
    ("YES", "YES"),
    ("NO", "NO"),
]
