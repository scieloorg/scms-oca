"""Observation dimension levels (Documentos / Periódicos) and value metrics."""

from django.utils.translation import gettext_lazy as _

LEVEL_DOCUMENTOS = "documentos"
LEVEL_PERIODICOS = "periodicos"

SCIENTIFIC_INDEX_NAMES = frozenset(
    {"scientific_production", "silver_scientific_production"}
)

# All scientific dimension slugs shown in the Documentos list (unchanged from before).
DOCUMENTOS_SLUGS = frozenset(
    {
        "documents-by-affiliation-region-world",
        "documents-by-affiliation-country",
        "documents-by-institution",
        "documents-by-publisher",
        "documents-by-journal",
        "documents-by-thematic-area",
        "documents-by-domain",
        "documents-by-subfield",
        "documents-by-document-type",
        "documents-by-document-language",
        "documents-by-open-access",
        "documents-by-access-type",
        "documents-by-source-type",
        "documents-by-source-country",
        "documents-by-funder",
    }
)

PERIODICOS_ONLY_SLUGS = frozenset(
    {
        "documents-by-indexed-in",
        "documents-by-scielo-indexed-in",
        "documents-by-scielo-collection",
        "documents-by-scope",
    }
)

PERIODICOS_SHARED_SLUGS = frozenset(
    {
        "documents-by-publisher",
        "documents-by-source-country",
        "documents-by-source-type",
    }
)

# Periódicos list (subset + periodicos-only dimensions).
PERIODICOS_SLUGS = PERIODICOS_ONLY_SLUGS | PERIODICOS_SHARED_SLUGS

JOURNAL_CARDINALITY_FIELD_CANDIDATES = (
    "source.issn_l",
    "source.ids.openalex",
    "source.title.keyword",
)


def observation_has_dimension_levels(index_name):
    return index_name in SCIENTIFIC_INDEX_NAMES


def observation_dimension_level_labels():
    return {
        LEVEL_DOCUMENTOS: _("Documents"),
        LEVEL_PERIODICOS: _("Journals"),
    }


def dimension_levels_for_slug(slug):
    levels = []
    if slug in DOCUMENTOS_SLUGS:
        levels.append(LEVEL_DOCUMENTOS)
    if slug in PERIODICOS_SLUGS:
        levels.append(LEVEL_PERIODICOS)
    return levels or [LEVEL_DOCUMENTOS]


def normalize_dimension_level(level):
    cleaned = str(level or LEVEL_DOCUMENTOS).strip().lower()
    if cleaned in (LEVEL_DOCUMENTOS, LEVEL_PERIODICOS):
        return cleaned
    return LEVEL_DOCUMENTOS


def dimension_value_metric(slug, level=LEVEL_DOCUMENTOS):
    level = normalize_dimension_level(level)
    if level == LEVEL_PERIODICOS:
        return "journals"
    return "documents"


def resolve_journal_cardinality_field(field_settings=None):
    field_settings = field_settings or {}
    for candidate in JOURNAL_CARDINALITY_FIELD_CANDIDATES:
        if candidate in {cfg.get("index_field_name") for cfg in field_settings.values()}:
            return candidate
    return JOURNAL_CARDINALITY_FIELD_CANDIDATES[0]
