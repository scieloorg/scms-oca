from django.utils.translation import gettext as _

FILTER_CATEGORIES = {
    "source": {
        "label": _("Source"),
        "icon": "icon-book",
        "order": 1,
    },
    "document": {
        "label": _("Document"),
        "icon": "icon-file-text",
        "order": 2,
    },
    "author_affiliation": {
        "label": _("Author Affiliation"),
        "icon": "icon-barcode",
        "order": 3,
    },
    "other": {
        "label": _("Other Filters"),
        "icon": "icon-filter",
        "order": 99,
    },
}
