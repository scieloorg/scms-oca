from django.conf import settings
from django.utils.translation import gettext_lazy as _

# Mapping from data source name to index and field settings
DATA_SOURCES = {
    "world": {
        "index_name": settings.ES_INDEX_SCI_PROD_WORLD,
        "display_name": _("Scientific Production - World"),
        "field_settings": {
            # General fields
            "source_index_open_alex": {
                "index_field_name": "indexed_in.keyword",
                "filter": {"size": 100, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Index (OpenAlex)"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "source_index_scielo": {
                "index_field_name": "primary_location.source.scl.indexed_in.keyword",
                "filter": {"size": 100, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Index (SciELO)"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "source_type": {
                "index_field_name": "primary_location.source.type.keyword",
                "filter": {
                    "size": 100,
                    "order": {"_key": "asc"},
                    "support_query_operator": False,
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            # Document fields
            "access_type": {
                "index_field_name": "open_access.oa_status.keyword",
                "filter": {
                    "size": 20,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Access Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "document_language": {
                "index_field_name": "language.keyword",
                "filter": {
                    "size": 100,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Language"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "document_type": {
                "index_field_name": "type.keyword",
                "filter": {
                    "size": 100,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "open_access": {
                "index_field_name": "open_access.is_oa",
                "filter": {
                    "size": 3,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Open Access"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "multiple_selection": False,
                },
            },
            "publication_year": {
                "index_field_name": "publication_year",
                "filter": {
                    "size": 100,
                    "order": {"_key": "desc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publication Year"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "document_publication_year_range": {
                "transform": "year_range",
                "source_fields": [
                    "document_publication_year_start",
                    "document_publication_year_end",
                ],
                "index_field_name": "publication_year",
                "settings": {
                    "class_filter": "range",
                    "label": _("Publication Year Range"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "subject_area_level_0": {
                "index_field_name": "thematic_areas.level0.keyword",
                "filter": {
                    "size": 3,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Subject Area Level 0"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "subject_area_level_1": {
                "index_field_name": "thematic_areas.level1.keyword",
                "filter": {
                    "size": 9,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Subject Area Level 1"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "subject_area_level_2": {
                "index_field_name": "thematic_areas.level2.keyword",
                "filter": {
                    "size": 41,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Subject Area Level 2"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            # Author affiliation fields
            "institution": {
                "index_field_name": "authorships.institutions.display_name.keyword",
                "filter": {
                    "size": 100,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Institution"),
                    "support_search_as_you_type": True,
                    "support_query_operator": True,
                },
            },
            "country": {
                "index_field_name": "authorships.countries.keyword",
                "filter": {
                    "size": 400,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Country"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                },
            },
            "region_world": {
                "index_field_name": "geos.scimago_regions.keyword",
                "filter": {
                    "size": 20,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Region (World)"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            # Metrics fields
            "cited_by_count": {
                "index_field_name": "cited_by_count",
                "filter": {
                    "size": 10,
                    "order": {"_key": "desc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Cited by Count"),
                    "support_query_operator": False,
                },
            },
            # External fields
            "source_country": {
                "index_field_name": "journal_metadata.country.keyword",
                "filter": {
                    "size": 300,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Country"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                },
            },
            "source_name": {
                "index_field_name": "primary_location.source.display_name.keyword",
                "filter": {
                    "size": 5,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Name"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "issn": {
                "index_field_name": "primary_location.source.issn.keyword",
                "filter": {
                    "size": 5,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("ISSN"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                },
            },
        },
    },
}


def get_data_source(data_source_name):
    """Get the full data source configuration."""
    return DATA_SOURCES.get(data_source_name.lower(), {})


def get_index_name_from_data_source(data_source):
    """Get the Elasticsearch index name for a data source."""
    return DATA_SOURCES.get(data_source, {}).get("index_name")


def get_index_field_name_from_data_source(data_source, field_name):
    """Get the Elasticsearch field name for a form field."""
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return field_settings[field_name].get("index_field_name")
    return field_name


def get_field_settings(data_source):
    """Get the field settings for a data source."""
    return DATA_SOURCES.get(data_source, {}).get("field_settings", {})


def get_display_fields(data_source):
    """Get the display fields for a data source."""
    return DATA_SOURCES.get(data_source, {}).get("display_fields", [])


def get_query_operator_fields(data_source):
    """Get the fields that support query operators for a given data source."""
    supported_query_fields = {}
    ds_field_settings = get_field_settings(data_source)

    if not ds_field_settings:
        return {}

    for field_name, data in ds_field_settings.items():
        if data.get("settings", {}).get("support_query_operator"):
            supported_query_fields[field_name] = data.get("index_field_name")

    return supported_query_fields


def field_supports_search_as_you_type(data_source, field_name):
    """Check if a field supports search-as-you-type functionality."""
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return (
            field_settings[field_name]
            .get("settings", {})
            .get("support_search_as_you_type", False)
        )
    return False


def get_size_by_field_name(data_source, field_name):
    """Get the aggregation size for a field."""
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return field_settings[field_name].get("filter", {}).get("size", 20)
    return 20


def get_label_by_field_name(data_source, field_name):
    """Get the display label for a field."""
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return field_settings[field_name].get("settings", {}).get("label")
    return field_name


def field_allows_multiple_selection(data_source, field_name):
    """Check if a field allows multiple selection."""
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return (
            field_settings[field_name]
            .get("settings", {})
            .get("multiple_selection", True)
        )
    return True