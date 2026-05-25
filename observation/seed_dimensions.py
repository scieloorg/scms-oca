"""Seed ObservationDimension rows from DataSource field_settings."""

from observation.models import ObservationDimension

SCIENTIFIC_TABLE_TITLE_PREFIX = (
    "Evolution of scientific production - World - number of documents by "
)
SOCIAL_TABLE_TITLE_PREFIX = "Brazil - Social Production - Country - Documents - "

DIMENSION_SPECS_BY_INDEX = {
    "scientific_production": [
        {
            "slug": "documents-by-affiliation-region-world",
            "menu_label": "Affiliation - Region of the World",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Affiliation - Region of the World",
            "row_label": "Region of the World",
            "row_field_candidates": [
                "world_region",
                "author_world_region",
                "region",
                "regions",
            ],
            "is_default": False,
        },
        {
            "slug": "documents-by-affiliation-country",
            "menu_label": "Affiliation \u2013 Country",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Affiliation \u2013 Country",
            "row_label": "Country",
            "row_field_candidates": ["country", "author_country_codes"],
            "is_default": True,
        },
        {
            "slug": "documents-by-institution",
            "menu_label": "Affiliation \u2013 Institution",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Affiliation \u2013 Institution",
            "row_label": "Institution",
            "row_field_candidates": ["institutions", "institution"],
            "is_default": False,
        },
        {
            "slug": "documents-by-publisher",
            "menu_label": "Publisher",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Publisher",
            "row_label": "Publisher",
            "row_field_candidates": ["publisher"],
            "is_default": False,
        },
        {
            "slug": "documents-by-journal",
            "menu_label": "Journal",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Journal",
            "row_label": "Journal",
            "row_field_candidates": ["source_name", "journal_title", "primary_source_title"],
            "is_default": False,
        },
        {
            "slug": "documents-by-thematic-area",
            "menu_label": "Thematic \u00e1rea",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Thematic \u00e1rea",
            "row_label": "Thematic \u00e1rea",
            "row_field_candidates": ["subject_area_level_1", "topic_fields", "primary_topic_field"],
            "is_default": False,
        },
        {
            "slug": "documents-by-domain",
            "menu_label": "Domain",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Domain",
            "row_label": "Domain",
            "row_field_candidates": [
                "subject_area_level_0",
                "primary_topic_domain",
                "topic_domains",
            ],
            "is_default": False,
        },
        {
            "slug": "documents-by-subfield",
            "menu_label": "Subfield",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Subfield",
            "row_label": "Subfield",
            "row_field_candidates": [
                "subject_area_level_2",
                "primary_topic_subfield",
                "topic_subfields",
            ],
            "is_default": False,
        },
        {
            "slug": "documents-by-document-type",
            "menu_label": "Document Type",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Document Type",
            "row_label": "Document Type",
            "row_field_candidates": ["document_type", "type"],
            "is_default": False,
        },
        {
            "slug": "documents-by-document-language",
            "menu_label": "Document Language",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Document Language",
            "row_label": "Document Language",
            "row_field_candidates": ["document_language", "language"],
            "is_default": False,
        },
        {
            "slug": "documents-by-open-access",
            "menu_label": "Open Access",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Open Access",
            "row_label": "Open Access",
            "row_field_candidates": ["open_access", "is_open_access"],
            "is_default": False,
        },
        {
            "slug": "documents-by-access-type",
            "menu_label": "Access Type",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Access Type",
            "row_label": "Access Type",
            "row_field_candidates": ["open_access_status"],
            "is_default": False,
        },
        {
            "slug": "documents-by-source-type",
            "menu_label": "Source Type",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Source Type",
            "row_label": "Source Type",
            "row_field_candidates": ["source_type"],
            "is_default": False,
        },
        {
            "slug": "documents-by-source-country",
            "menu_label": "Source Country",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Source Country",
            "row_label": "Source Country",
            "row_field_candidates": ["source_country"],
            "is_default": False,
        },
        {
            "slug": "documents-by-funder",
            "menu_label": "Funder",
            "table_title": f"{SCIENTIFIC_TABLE_TITLE_PREFIX}Funder",
            "row_label": "Funder",
            "row_field_candidates": ["funder", "funders"],
            "is_default": False,
        },
    ],
    "social_production": [
        {
            "slug": "documents-by-events",
            "menu_label": "Events",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Events",
            "row_label": "Types",
            "row_field_candidates": ["directory_type", "type"],
            "is_default": True,
        },
        {
            "slug": "documents-by-institutions",
            "menu_label": "Institutions",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Institutions",
            "row_label": "Institutions",
            "row_field_candidates": ["institutions"],
            "is_default": False,
        },
        {
            "slug": "documents-by-states",
            "menu_label": "States",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}States",
            "row_label": "States",
            "row_field_candidates": ["states"],
            "is_default": False,
        },
        {
            "slug": "documents-by-regions",
            "menu_label": "Regions",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Regions",
            "row_label": "Regions",
            "row_field_candidates": ["regions"],
            "row_field_fallback": "regions",
            "is_default": False,
        },
        {
            "slug": "documents-by-cities",
            "menu_label": "Cities",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Cities",
            "row_label": "Cities",
            "row_field_candidates": ["cities"],
            "is_default": False,
        },
        {
            "slug": "documents-by-action",
            "menu_label": "Action",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Action",
            "row_label": "Action",
            "row_field_candidates": ["action"],
            "is_default": False,
        },
        {
            "slug": "documents-by-practice",
            "menu_label": "Practice",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Practice",
            "row_label": "Practice",
            "row_field_candidates": ["practice"],
            "is_default": False,
        },
        {
            "slug": "documents-by-classification",
            "menu_label": "Classification",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Classification",
            "row_label": "Classification",
            "row_field_candidates": ["classification"],
            "is_default": False,
        },
        {
            "slug": "documents-by-division",
            "menu_label": "Division",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Division",
            "row_label": "Division",
            "row_field_candidates": ["thematic_level_0"],
            "is_default": False,
        },
        {
            "slug": "documents-by-area",
            "menu_label": "Area",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Area",
            "row_label": "Area",
            "row_field_candidates": ["thematic_level_1"],
            "is_default": False,
        },
        {
            "slug": "documents-by-subarea",
            "menu_label": "Subarea",
            "table_title": f"{SOCIAL_TABLE_TITLE_PREFIX}Subarea",
            "row_label": "Subarea",
            "row_field_candidates": ["thematic_level_2"],
            "is_default": False,
        },
    ],
}


def _pick_row_field(field_settings, candidates):
    for candidate in candidates:
        if candidate in field_settings:
            return candidate
    return None


def _write(stdout, style, message):
    if stdout is None:
        return
    if style:
        stdout.write(style(message))
    else:
        stdout.write(f"{message}\n")


def seed_observation_page_dimensions(page, *, stdout=None, style=None):
    """
    Create or update dimensions for one ObservationPage.

    Returns the number of dimensions created/updated, or 0 if skipped.
    """
    if not page.data_source:
        _write(
            stdout,
            getattr(style, "WARNING", None) if style else None,
            f"[page={page.id}] skipped: page has no data_source.",
        )
        return 0

    field_settings = page.data_source.field_settings_dict or {}
    created_or_updated = 0
    default_slug = None
    preferred_default_slugs = []

    dimension_specs = DIMENSION_SPECS_BY_INDEX.get(page.data_source.index_name)
    if dimension_specs is None:
        dimension_specs = DIMENSION_SPECS_BY_INDEX["scientific_production"]

    expected_slugs = {spec["slug"] for spec in dimension_specs}
    removed, _ = page.dimensions.exclude(slug__in=expected_slugs).delete()
    if removed:
        _write(
            stdout,
            getattr(style, "WARNING", None) if style else None,
            f"[page={page.id}] removed {removed} obsolete dimension(s).",
        )

    for spec in dimension_specs:
        if spec.get("is_default"):
            preferred_default_slugs.append(spec["slug"])

        row_field_name = _pick_row_field(field_settings, spec["row_field_candidates"])
        if not row_field_name:
            row_field_name = spec.get("row_field_fallback")
        if not row_field_name:
            _write(
                stdout,
                getattr(style, "WARNING", None) if style else None,
                f"[page={page.id}] skipped dimension '{spec['slug']}': "
                f"none of {spec['row_field_candidates']} exists in DataSource.",
            )
            continue

        col_field_name = "publication_year"
        if col_field_name not in field_settings:
            _write(
                stdout,
                getattr(style, "WARNING", None) if style else None,
                f"[page={page.id}] skipped dimension '{spec['slug']}': "
                "publication_year not configured in DataSource.",
            )
            continue

        defaults = {
            "menu_label": spec["menu_label"],
            "row_field_name": row_field_name,
            "col_field_name": col_field_name,
            "row_bucket_size": 500,
            "col_bucket_size": 300,
            "table_title": spec["table_title"],
            "kpi_label": "Documents",
            "row_label": spec["row_label"],
            "col_label": "Year",
            "value_label": "Documents",
            "is_default": False,
        }
        ObservationDimension.objects.update_or_create(
            page=page,
            slug=spec["slug"],
            defaults=defaults,
        )
        created_or_updated += 1
        if spec.get("is_default"):
            default_slug = spec["slug"]

    if not default_slug:
        for slug in preferred_default_slugs:
            if page.dimensions.filter(slug=slug).exists():
                default_slug = slug
                break

    if not default_slug:
        default_slug = (
            page.dimensions.order_by("sort_order", "id")
            .values_list("slug", flat=True)
            .first()
        )

    if default_slug:
        page.dimensions.exclude(slug=default_slug).update(is_default=False)
        page.dimensions.filter(slug=default_slug).update(is_default=True)

    _write(
        stdout,
        getattr(style, "SUCCESS", None) if style else None,
        f"[page={page.id}] dimensions created/updated: {created_or_updated}",
    )
    return created_or_updated


def seed_all_observation_pages(*, stdout=None, style=None):
    """
    Seed dimensions once per Wagtail translation group (translation_key).

    Other locales reuse dimensions via ObservationPage.get_dimensions_config().
    """
    from observation.models import ObservationPage

    pages = list(
        ObservationPage.objects.select_related("data_source", "locale")
        .filter(data_source__isnull=False)
        .order_by("translation_key", "id")
    )
    seen_translation_keys = set()
    page_count = 0
    total = 0
    for page in pages:
        if page.translation_key in seen_translation_keys:
            continue
        seen_translation_keys.add(page.translation_key)
        page_count += 1
        total += seed_observation_page_dimensions(page, stdout=stdout, style=style)
    return page_count, total
