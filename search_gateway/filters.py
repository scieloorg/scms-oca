from django.utils.translation import gettext as _

FILTER_CATEGORIES = {
    "scope": {
        "label": _("Data scope"),
        "icon": "icon-filter",
        "order": 1,
    },
    "indexing": {
        "label": _("Indexing"),
        "icon": "icon-filter",
        "order": 2,
    },
    "source": {
        "label": _("Source Identity"),
        "icon": "icon-book",
        "order": 3,
    },
    "document": {
        "label": _("Document"),
        "icon": "icon-file-text",
        "order": 4,
    },
    "category": {
        "label": _("Category"),
        "icon": "icon-file-text",
        "order": 5,
    },    
    "author_affiliation": {
        "label": _("Author Affiliation"),
        "icon": "icon-barcode",
        "order": 6,
    },
    "other": {
        "label": _("Other Filters"),
        "icon": "icon-filter",
        "order": 99,
    },
}
