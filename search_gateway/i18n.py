from django.utils.translation import gettext_noop


# Fixture-backed labels are stored in JSON and translated at runtime, so we
# register their msgids here to keep them in the translation catalogs.
DATASOURCE_FIXTURE_MSGIDS = [
    gettext_noop("Publishing Model"),
    gettext_noop("Timeline"),
    gettext_noop("Activity Profile"),
    gettext_noop("Thematic Scope"),
    gettext_noop("Document Identity"),
    gettext_noop("Source Coverage"),
    gettext_noop("Minimum publications"),
]
