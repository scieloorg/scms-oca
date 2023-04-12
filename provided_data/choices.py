from django.utils.translation import gettext as _

DOCUMENT_TYPES = [
    ("", ""),
    ("conference proceedings", _("Conference Proceedings")),
    ("journal article", _("Journal Article")),
    ("master thesis", _("Master Thesis")),
    ("doctoral thesis", _("Doctoral Thesis")),
]

NAME_TYPES = [
    ("", ""),
    ("name", _("Name")),
    ("citation name", _("Citation Name")),
]

LEVELS = [
    ("", ""),
    ("UNDEFINED", _("UNDEFINED")),
    ("0", _("Level 0")),
    ("1", _("Level 1")),
    ("2", _("Level 2")),
    ("3", _("Level 3")),
]
