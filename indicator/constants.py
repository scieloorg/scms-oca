from django.conf import settings


# Mapping from form fields to Elasticsearch index fields for each data source
DSNAME_TO_FIELD_SETTINGS = {
    # openalex_works without country restriction
    settings.DSNAME_SCI_PROD_WORLD: {
        # General fields
        "source_index_open_alex": {"index_field_name": "indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_index_scielo": {"index_field_name": "primary_location.source.scl.indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
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
        "institution": {"index_field_name": "authorships.institutions.display_name.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "country": {"index_field_name": "authorships.countries.keyword", "filter": {"size": 400, "order": {"_key": "asc"}, "support_query_operator": True}},
        "region_world": {"index_field_name": "geos.scimago_regions.keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Metrics fields
        "cited_by_count": {"index_field_name": "cited_by_count", "filter": {"size": 10, "order": {"_key": "desc"}, "support_query_operator": False}},
        # External fields
        "source_country": {"index_field_name": "journal_metadata.country.keyword", "filter": {"size": 300, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "source_name": {"index_field_name": "primary_location.source.display_name.keyword", "filter": {"size": 5, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "issn": {"index_field_name": "primary_location.source.issn.keyword", "filter": {"size": 5, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}}
    },
    # openalex_works restricted to Brazil
    settings.DSNAME_SCI_PROD_BRAZIL: {
        # General fields
        "source_index_open_alex": {"index_field_name": "indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_index_scielo": {"index_field_name": "primary_location.source.scl.indexed_in.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
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
        "institution": {"index_field_name": "authorships.institutions.display_name.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "country": {"index_field_name": "authorships.countries.keyword", "filter": {"size": 400, "order": {"_key": "asc"}, "support_query_operator": True}},
        "region_world": {"index_field_name": "geos.scimago_regions.keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Metrics fields
        "cited_by_count": {"index_field_name": "cited_by_count", "filter": {"size": 10, "order": {"_key": "desc"}, "support_query_operator": False}},
        # External fields
        "source_country": {"index_field_name": "journal_metadata.country.keyword", "filter": {"size": 300, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "source_name": {"index_field_name": "primary_location.source.display_name.keyword", "filter": {"size": 5, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "issn": {"index_field_name": "primary_location.source.issn.keyword", "filter": {"size": 5, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
    },
    # scielo_works
    settings.DSNAME_SCI_PROD_SCIELO: {
        "collection": {"index_field_name": "collection.keyword", "filter": {"size": 30, "order": {"_key": "asc"}, "support_query_operator": False}},
        "publisher": {"index_field_name": "publisher.keyword", "filter": {"size": 1, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "journal": {"index_field_name": "journal.keyword", "filter": {"size": 1, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        # Document fields
        "access_type": {"index_field_name": "open_access_oa_status.keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
        "document_language": {"index_field_name": "languages.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": True}},
        "document_type": {"index_field_name": "type.keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "publication_year": {"index_field_name": "publication_year", "filter": {"size": 100, "order": {"_key": "desc"}, "support_query_operator": False}},
        # Author affiliation fields
        "country": {"index_field_name": "authorships_countries.keyword", "filter": {"size": 300, "order": {"_key": "asc"}, "support_query_operator": True}},
        "institution": {"index_field_name": "authorships_institutions_display_name.keyword", "filter": {"size": 1, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        # Metrics fields
        "cited_by_count": {"index_field_name": "openalex_cited_by_count", "filter": {"size": 10, "order": {"_key": "desc"}, "support_query_operator": False}},
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
    # journal_metrics
    settings.DSNAME_JOURNAL_METRICS: {
        # Journal identification fields
        "country": {"index_field_name": "country", "field_type": "keyword", "filter": {"size": 300, "order": {"_key": "asc"}, "support_query_operator": False}},
        "journal": {"index_field_name": "journal.keyword", "filter": {"size": 1, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": True}},
        "openalex_region": {"index_field_name": "openalex_region", "field_type": "keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}}, 
        "publisher_name": {"index_field_name": "publisher_name.keyword", "filter": {"size": 1, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": True}},
        "scielo_collection_name": {"index_field_name": "scielo_collection_name", "field_type": "keyword", "filter": {"size": 100, "order": {"_key": "asc"}, "support_query_operator": False}},
        "scielo_thematic_area": {"index_field_name": "scielo_thematic_areas", "field_type": "keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": True}},
        "scimago_region": {"index_field_name": "scimago_region", "field_type": "keyword", "filter": {"size": 20, "order": {"_key": "asc"}, "support_query_operator": False}},
        "source_index": {"index_field_name": "source", "field_type": "keyword", "filter": {"size": 10, "order": {"_key": "asc"}, "support_query_operator": True}},
        "issn": {"index_field_name": "issns", "filter": {"size": 1, "order": {"_key": "desc"}, "support_query_operator": False, "support_search_as_you_type": True}},
        "year_founded": {"index_field_name": "year_of_creation_of_the_periodical", "filter": {"size": 1000, "order": {"_key": "desc"}, "support_query_operator": False}},
        "is_scielo": {"index_field_name": "is_scielo", "filter": {"size": 3, "order": {"_key": "asc"}, "support_query_operator": False}},
        # Journal metric fields 
        "year": {"index_field_name": "year", "filter": {"size": 100, "order": {"_key": "desc"}, "support_query_operator": False}},
        "cwts_snip": {"index_field_name": "cwts_snip", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "openalex_num_docs": {"index_field_name": "openalex_num_docs", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},        
        "scielo_num_docs": {"index_field_name": "scielo_num_docs", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_best_quartile": {"index_field_name": "scimago_best_quartile.keyword", "filter": {"use": False, "size": 1, "order": {"_key": "asc"}, "support_query_operator": False}},
        "scimago_citable_docs_3_years": {"index_field_name": "scimago_citable_docs_3_years", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_cites_by_doc_2_years": {"index_field_name": "scimago_cites_by_doc_2_years", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_estimated_apc": {"index_field_name": "scimago_estimated_apc", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_estimated_value": {"index_field_name": "scimago_estimated_value", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_female_authors_percent": {"index_field_name": "scimago_female_authors_percent", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_overton": {"index_field_name": "scimago_overton", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_sdg": {"index_field_name": "scimago_sdg", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_sjr": {"index_field_name": "scimago_sjr", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_total_cites_3_years": {"index_field_name": "scimago_total_cites_3_years", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
        "scimago_total_docs_3_years": {"index_field_name": "scimago_total_docs_3_years", "filter": {"use": False, "size": 1, "order": {"_key": "desc"}, "support_query_operator": False}},
    },
    # sources
    settings.DSNAME_SOURCES: {
        "source_country": {"index_field_name": "country.keyword", "filter": {"size": 300, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "source_name": {"index_field_name": "display_name.keyword", "filter": {"size": 5, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
        "issn": {"index_field_name": "issn.keyword", "filter": {"size": 5, "order": {"_key": "asc"}, "support_query_operator": False, "support_search_as_you_type": False}},
    }
}
