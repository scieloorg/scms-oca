"""Server-side i18n for observation dimension UI labels (listbox, table, KPI, JSON)."""

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from observation.dimension_groups import (
    LEVEL_PERIODICOS,
    dimension_value_metric,
    normalize_dimension_level,
)

_COMMON_KPI = _("Documents")
_COMMON_JOURNAL_KPI = _("Journals")
_COMMON_COL = _("Year")
_COMMON_VALUE = _("Documents")
_COMMON_JOURNAL_VALUE = _("Journals")

OBSERVATION_LEVEL_SELECT_LABEL = _("Level")

OBSERVATION_SELECT_LABEL_SCIENTIFIC = _("Select an observation table:")
OBSERVATION_SELECT_LABEL_SOCIAL = _(
    "Select an observation table on social production in Brazil by:"
)
OBSERVATION_SELECT_LABEL_DEFAULT = _("Select an observation table")

# Fallback configs when no ObservationDimension rows exist (msgids match seed / DB).
FALLBACK_DIMENSION_BY_INDEX = {
    "scientific_production": {
        "slug": "documents-by-affiliation-country",
        "menu_label": "Affiliation \u2013 Country",
        "row_field_name": "country",
        "col_field_name": "publication_year",
        "row_bucket_size": 500,
        "col_bucket_size": 300,
        "table_title": (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Country"
        ),
        "kpi_label": "Documents",
        "row_label": "Country",
        "col_label": "Year",
        "value_label": "Documents",
    },
    "social_production": {
        "slug": "documents-by-events",
        "menu_label": "Events",
        "row_field_name": "directory_type",
        "col_field_name": "publication_year",
        "row_bucket_size": 500,
        "col_bucket_size": 300,
        "table_title": "Brazil - Social Production - Country - Documents - Events",
        "kpi_label": "Documents",
        "row_label": "Types",
        "col_label": "Year",
        "value_label": "Documents",
        "is_default": True,
    },
}
FALLBACK_DIMENSION_BY_INDEX["silver_scientific_production"] = FALLBACK_DIMENSION_BY_INDEX["scientific_production"]


# Slug → lazy msgids (extracted by makemessages). DB seed values must match these msgids.
DIMENSION_I18N = {
    "documents-by-affiliation-region-world": {
        "menu_label": _("Affiliation - Region of the World"),
        "row_label": _("Region of the World"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by "
            "Affiliation - Region of the World"
        ),
    },
    "documents-by-affiliation-country": {
        "menu_label": _("Affiliation \u2013 Country"),
        "row_label": _("Country"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Country"
        ),
    },
    "documents-by-institution": {
        "menu_label": _("Affiliation \u2013 Institution"),
        "row_label": _("Institution"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Institution"
        ),
    },
    "documents-by-publisher": {
        "menu_label": _("Publisher"),
        "row_label": _("Publisher"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Publisher"
        ),
    },
    "documents-by-journal": {
        "menu_label": _("Journal"),
        "row_label": _("Journal"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Journal"
        ),
    },
    "documents-by-thematic-area": {
        "menu_label": _("Thematic \u00e1rea"),
        "row_label": _("Thematic \u00e1rea"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by "
            "Thematic \u00e1rea"
        ),
    },
    "documents-by-domain": {
        "menu_label": _("Domain"),
        "row_label": _("Domain"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Domain"
        ),
    },
    "documents-by-subfield": {
        "menu_label": _("Subfield"),
        "row_label": _("Subfield"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Subfield"
        ),
    },
    "documents-by-document-type": {
        "menu_label": _("Document Type"),
        "row_label": _("Document Type"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Document Type"
        ),
    },
    "documents-by-document-language": {
        "menu_label": _("Document Language"),
        "row_label": _("Document Language"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by "
            "Document Language"
        ),
    },
    "documents-by-open-access": {
        "menu_label": _("Open Access"),
        "row_label": _("Open Access"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Open Access"
        ),
    },
    "documents-by-access-type": {
        "menu_label": _("Access Type"),
        "row_label": _("Access Type"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Access Type"
        ),
    },
    "documents-by-source-type": {
        "menu_label": _("Source Type"),
        "row_label": _("Source Type"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Source Type"
        ),
    },
    "documents-by-source-country": {
        "menu_label": _("Source Country"),
        "row_label": _("Source Country"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by "
            "Source Country"
        ),
    },
    "documents-by-funder": {
        "menu_label": _("Funder"),
        "row_label": _("Funder"),
        "table_title": _(
            "Evolution of scientific production - World - number of documents by Funder"
        ),
    },
    "documents-by-indexed-in": {
        "menu_label": _("Indexed In (OpenAlex)"),
        "row_label": _("Indexed In (OpenAlex)"),
        "table_title": _(
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (OpenAlex)"
        ),
    },
    "documents-by-scielo-indexed-in": {
        "menu_label": _("Indexed In (SciELO)"),
        "row_label": _("Indexed In (SciELO)"),
        "table_title": _(
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (SciELO)"
        ),
    },
    "documents-by-scielo-collection": {
        "menu_label": _("SciELO Collection"),
        "row_label": _("SciELO Collection"),
        "table_title": _(
            "Evolution of scientific production - World - number of journals by "
            "SciELO Collection"
        ),
    },
    "documents-by-scope": {
        "menu_label": _("Scope"),
        "row_label": _("Scope"),
        "table_title": _(
            "Evolution of scientific production - World - number of journals by Scope"
        ),
    },
    "documents-by-events": {
        "menu_label": _("Events"),
        "row_label": _("Types"),
        "table_title": _("Brazil - Social Production - Country - Documents - Events"),
    },
    "documents-by-institutions": {
        "menu_label": _("Institutions"),
        "row_label": _("Institutions"),
        "table_title": _(
            "Brazil - Social Production - Country - Documents - Institutions"
        ),
    },
    "documents-by-states": {
        "menu_label": _("States"),
        "row_label": _("States"),
        "table_title": _("Brazil - Social Production - Country - Documents - States"),
    },
    "documents-by-regions": {
        "menu_label": _("Regions"),
        "row_label": _("Regions"),
        "table_title": _("Brazil - Social Production - Country - Documents - Regions"),
    },
    "documents-by-cities": {
        "menu_label": _("Cities"),
        "row_label": _("Cities"),
        "table_title": _("Brazil - Social Production - Country - Documents - Cities"),
    },
    "documents-by-action": {
        "menu_label": _("Action"),
        "row_label": _("Action"),
        "table_title": _("Brazil - Social Production - Country - Documents - Action"),
    },
    "documents-by-practice": {
        "menu_label": _("Practice"),
        "row_label": _("Practice"),
        "table_title": _("Brazil - Social Production - Country - Documents - Practice"),
    },
    "documents-by-classification": {
        "menu_label": _("Classification"),
        "row_label": _("Classification"),
        "table_title": _(
            "Brazil - Social Production - Country - Documents - Classification"
        ),
    },
    "documents-by-division": {
        "menu_label": _("Division"),
        "row_label": _("Division"),
        "table_title": _("Brazil - Social Production - Country - Documents - Division"),
    },
    "documents-by-area": {
        "menu_label": _("Area"),
        "row_label": _("Area"),
        "table_title": _("Brazil - Social Production - Country - Documents - Area"),
    },
    "documents-by-subarea": {
        "menu_label": _("Subarea"),
        "row_label": _("Subarea"),
        "table_title": _("Brazil - Social Production - Country - Documents - Subarea"),
    },
}

# Journal-metric titles for shared slugs when level = Periódicos.
DIMENSION_JOURNAL_I18N = {
    "documents-by-publisher": {
        "table_title": _(
            "Evolution of scientific production - World - number of journals by Publisher"
        ),
    },
    "documents-by-source-type": {
        "table_title": _(
            "Evolution of scientific production - World - number of journals by Source Type"
        ),
    },
    "documents-by-source-country": {
        "table_title": _(
            "Evolution of scientific production - World - number of journals by "
            "Source Country"
        ),
    },
}

_LABEL_FIELDS = (
    "menu_label",
    "table_title",
    "row_label",
    "kpi_label",
    "col_label",
    "value_label",
)


def observation_dimension_select_label(index_name):
    if index_name in ("scientific_production", "silver_scientific_production"):
        return gettext(OBSERVATION_SELECT_LABEL_SCIENTIFIC)
    if index_name == "social_production":
        return gettext(OBSERVATION_SELECT_LABEL_SOCIAL)
    return gettext(OBSERVATION_SELECT_LABEL_DEFAULT)


def fallback_dimension_for_index(index_name):
    spec = FALLBACK_DIMENSION_BY_INDEX.get(index_name)
    if spec is None:
        spec = FALLBACK_DIMENSION_BY_INDEX["scientific_production"]
    return localize_dimension(dict(spec))


def localize_dimension(dimension, level=None):
    """Apply gettext to display fields for the active request locale."""
    if not dimension:
        return dimension

    localized = dict(dimension)
    slug = localized.get("slug") or ""
    level = normalize_dimension_level(level or localized.get("dimension_level"))
    spec = DIMENSION_I18N.get(slug)

    if spec:
        for field in _LABEL_FIELDS:
            if field in spec:
                localized[field] = gettext(spec[field])
        localized.setdefault("kpi_label", gettext(_COMMON_KPI))
        localized.setdefault("col_label", gettext(_COMMON_COL))
        localized.setdefault("value_label", gettext(_COMMON_VALUE))
    else:
        for field in _LABEL_FIELDS:
            value = localized.get(field)
            if isinstance(value, str) and value.strip():
                localized[field] = gettext(value)

    if level == LEVEL_PERIODICOS and dimension_value_metric(slug, level) == "journals":
        journal_spec = DIMENSION_JOURNAL_I18N.get(slug, {})
        if journal_spec.get("table_title"):
            localized["table_title"] = gettext(journal_spec["table_title"])
        localized["kpi_label"] = gettext(_COMMON_JOURNAL_KPI)
        localized["value_label"] = gettext(_COMMON_JOURNAL_VALUE)

    localized["dimension_level"] = level
    localized["value_metric"] = dimension_value_metric(slug, level)
    return localized


def localize_dimension_for_level(dimension, level):
    return localize_dimension(dimension, level=level)
