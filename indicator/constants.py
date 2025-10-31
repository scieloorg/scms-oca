from django.conf import settings


# Mapping from form fields to Elasticsearch index fields for each data source
DSNAME_TO_FIELD_SETTINGS = {
    # openalex_works without country restriction
    settings.DSNAME_SCI_PROD_WORLD: {
        # General fields
        "source_index_open_alex": {"index_field_name": "indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_index_scielo": {"index_field_name": "primary_location.source.scl.indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_name": {"index_field_name": "primary_location.source.display_name.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_type": {"index_field_name": "primary_location.source.type.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Document fields
        "access_type": {"index_field_name": "open_access.oa_status.keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
        "document_language": {"index_field_name": "language.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "document_type": {"index_field_name": "type.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "open_access": {"index_field_name": "open_access.is_oa", "filter": {"size": 3, "order": {"_key": "asc"}, "support_query_operator": False}},
        "publication_year": {"index_field_name": "publication_year", "filter": {"size": 100, "order": {"_key": "desc"}, "support_query_operator": False}},
        "subject_area_level_0": {"index_field_name": "thematic_areas.level0.keyword", "filter": {"size": 3, "order": {"_key": "asc"}, "support_query_operator": False}},
        "subject_area_level_1": {"index_field_name": "thematic_areas.level1.keyword", "filter": {"size": 9, "order": {"_key": "asc"}, "support_query_operator": False}},
        "subject_area_level_2": {"index_field_name": "thematic_areas.level2.keyword", "filter": {"size": 41, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Author affiliation fields
        "country": {"index_field_name": "authorships.countries.keyword", "filter": {"size": 400, "order": {"_key": "asc"}, "support_query_operator": True}},
        "region_world": {"index_field_name": "geos.scimago_regions.keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
    },
    # openalex_works restricted to Brazil
    settings.DSNAME_SCI_PROD_BRAZIL: {
        # General fields
        "source_index_open_alex": {"index_field_name": "indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_index_scielo": {"index_field_name": "primary_location.source.scl.indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_name": {"index_field_name": "primary_location.source.display_name.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_type": {"index_field_name": "primary_location.source.type.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Document fields
        "access_type": {"index_field_name": "open_access.oa_status.keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
        "document_language": {"index_field_name": "language.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "document_type": {"index_field_name": "type.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "open_access": {"index_field_name": "open_access.is_oa", "filter": {"size": 3, "order": {"_key": "asc"}, "support_query_operator": False}},
        "publication_year": {"index_field_name": "publication_year", "filter": {"size": 100, "order": {"_key": "desc"}, "support_query_operator": False}},
        "subject_area_level_0": {"index_field_name": "thematic_areas.level0.keyword", "filter": {"size": 3, "order": {"_key": "asc"}, "support_query_operator": False}},
        "subject_area_level_1": {"index_field_name": "thematic_areas.level1.keyword", "filter": {"size": 9, "order": {"_key": "asc"}, "support_query_operator": False}},
        "subject_area_level_2": {"index_field_name": "thematic_areas.level2.keyword", "filter": {"size": 41, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Author affiliation fields
        "country": {"index_field_name": "authorships.countries.keyword", "filter": {"size": 400, "order": {"_key": "asc"}, "support_query_operator": True}},
        "region_world": {"index_field_name": "geos.scimago_regions.keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
    },
    # scielo_works
    settings.DSNAME_SCI_PROD_SCIELO: {
        "collection": {"index_field_name": "collection.enum", "filter": {"size": 30, "order": {"_key": "asc"}, "support_query_operator": False}},
        "journal": {"index_field_name": "journal.enum", "filter": {"size": 2500, "order": {"_key": "asc"}, "support_query_operator": False}},
        "publisher": {"index_field_name": "publisher.enum", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Document fields
        "access_type": {"index_field_name": "open_access.oa_status.enum", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
        "document_language": {"index_field_name": "languages.enum", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": True}},
        "document_type": {"index_field_name": "type.enum", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "publication_year": {"index_field_name": "publication_year", "filter": {"size": 100, "order": {"_key": "desc"}, "support_query_operator": False}},
        # Author affiliation fields
        "country": {"index_field_name": "authorships.countries.enum", "filter": {"size": 300, "order": {"_key": "asc"}, "support_query_operator": True}},
        "institution": {"index_field_name": "authorships.institutions.display_name.enum", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
    },
    # opoca
    settings.DSNAME_SOC_PROD: {
        "publication_year": {"index_field_name": "year", "filter":{"size": 1000, "order": {"_key": "desc"}, "support_query_operator": False}},
        "city_brazil": {"index_field_name": "cities.enum", "filter":{"size": 1000, "order": {"_key": "asc"}, "support_query_operator": False}},
        "state_brazil": {"index_field_name": "states.enum", "filter":{"size": 27, "order": {"_key": "asc"}, "support_query_operator": False}},
        "action": {"index_field_name": "action.enum", "filter":{"size": 1000, "order": {"_key": "asc"}, "support_query_operator": False}},
        "classification": {"index_field_name": "classification.enum", "filter":{"size": 1000, "order": {"_key": "asc"}, "support_query_operator": False}},
        "directory_type": {"index_field_name": "directory_type.enum", "filter":{"size": 1000, "order": {"_key": "asc"}, "support_query_operator": False}},
        "institution": {"index_field_name": "institutions.enum", "filter":{"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "practice": {"index_field_name": "practice.enum", "filter":{"size": 1000, "order": {"_key": "asc"}, "support_query_operator": False}},
    },
}
