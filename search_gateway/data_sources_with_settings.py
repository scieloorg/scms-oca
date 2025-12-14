from django.conf import settings
from django.utils.translation import gettext_lazy as _

# Mapping from data source name to index and field settings
DATA_SOURCES = {
    "world": {
        "index_name": settings.ES_INDEX_SCI_PROD_WORLD,
        "display_name": _("Scientific Production - World"),
        "source_fields" : [
            "_id",
            "primary_location",
            "publication_year",
            "biblio.volume",
            "biblio.issue",
            "biblio.first_page",
            "journal_metadata.issns",
            "journal_metadata.country",
            "title",
            "authorships",
            "language",
            "type",
            "open_access.is_oa",
            "open_access.oa_status",
            "indexed_in",
            "locations.landing_page_url",            
        ],
        "filters_to_exclude": [
            "source_index_scielo",
            "cited_by_count",
            "document_publication_year_start",
            "document_publication_year_end",
            "document_publication_year_range"            
        ],
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
                    "display_transform": "language",
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
                    "transform": {
                      "type": "boolean"
                    },
                    "size": 3,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Open Access"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "multiple_selection": False,
                    "display_transform": "boolean",
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
            "document_publication_year_start": {
                "index_field_name": "publication_year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_publication_year_end": {
                "index_field_name": "publication_year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                }
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
                    "size": 5,
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
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "display_transform": "country",
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
                    "size": 1,
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
    "brazil": {
        "index_name": settings.ES_INDEX_SCI_PROD_BRAZIL,
        "display_name": _("Scientific Production - Brazil"),
        "field_settings": {
            "source_index_open_alex": {
                "index_field_name": "indexed_in.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "source_index_scielo": {
                "index_field_name": "primary_location.source.scl.indexed_in.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "source_type": {
                "index_field_name": "primary_location.source.type.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "access_type": {
                "index_field_name": "open_access.oa_status.keyword",
                "filter": {
                    "size": 20,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_language": {
                "index_field_name": "language.keyword",
                "filter": {
                    "size": 200,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_type": {
                "index_field_name": "type.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
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
            "document_publication_year_start": {
                "index_field_name": "publication_year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_publication_year_end": {
                "index_field_name": "publication_year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "open_access": {
                "index_field_name": "open_access.is_oa",
                "filter": {
                    "transform": {
                        "type": "boolean"
                    },
                    "size": 2,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "subject_area_level_0": {
                "index_field_name": "thematic_areas.level0.keyword",
                "filter": {
                    "size": 10,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "subject_area_level_1": {
                "index_field_name": "thematic_areas.level1.keyword",
                "filter": {
                    "size": 20,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "subject_area_level_2": {
                "index_field_name": "thematic_areas.level2.keyword",
                "filter": {
                    "size": 50,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "institution": {
                "index_field_name": "authorships.institutions.display_name.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "country": {
                "index_field_name": "authorships.countries.keyword",
                "filter": {
                    "size": 400,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "support_query_operator": True
                }
            },
            "region_world": {
                "index_field_name": "geos.scimago_regions.keyword",
                "filter": {
                    "size": 20,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "cited_by_count": {
                "index_field_name": "cited_by_count",
                "filter": {
                    "size": 10,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "source_country": {
                "index_field_name": "journal_metadata.country.keyword",
                "filter": {
                    "size": 300,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "source_name": {
                "index_field_name": "primary_location.source.display_name.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "issn": {
                "index_field_name": "primary_location.source.issn.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            }
        }
    },
    "scielo": {
        "index_name": settings.ES_INDEX_SCI_PROD_SCIELO,
        "display_name": _("Scientific Production - SciELO Network"),
        "field_settings": {
            "collection": {
                "index_field_name": "collection.keyword",
                "filter": {
                    "size": 50,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "publisher": {
                "index_field_name": "publisher.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "journal": {
                "index_field_name": "journal.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "access_type": {
                "index_field_name": "open_access_oa_status.keyword",
                "filter": {
                    "size": 20,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_language": {
                "index_field_name": "languages.keyword",
                "filter": {
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "support_query_operator": True
                }
            },
            "document_type": {
                "index_field_name": "type.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_publication_year_start": {
                "index_field_name": "publication_year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_publication_year_end": {
                "index_field_name": "publication_year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "country": {
                "index_field_name": "authorships_countries.keyword",
                "filter": {
                    "size": 300,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "support_query_operator": True
                }
            },
            "institution": {
                "index_field_name": "authorships_institutions_display_name.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "cited_by_count": {
                "index_field_name": "openalex_cited_by_count",
                "filter": {
                    "size": 10,
                    "order": {
                        "_key": "desc"
                    },
                }
            }
        }
    },
    "social": {
        "index_name": settings.ES_INDEX_SOC_PROD,
        "display_name": _("Social Production"),
        "field_settings": {
            "document_publication_year_start": {
                "index_field_name": "year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "document_publication_year_end": {
                "index_field_name": "year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "city_brazil": {
                "index_field_name": "cities.enum",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "state_brazil": {
                "index_field_name": "states.enum",
                "filter": {
                    "size": 27,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "action": {
                "index_field_name": "action.enum",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "classification": {
                "index_field_name": "classification.enum",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "directory_type": {
                "index_field_name": "directory_type.enum",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "institution": {
                "index_field_name": "institutions.enum",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "practice": {
                "index_field_name": "practice.enum",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
        }
    },
    "social_production": {
        "index_name": settings.ES_INDEX_SOCIAL_PRODUCTION,
        "display_name": _("Social Production"),
        "source_fields": ["*"],
        "filters_to_exclude": [
            "document_publication_year_end"
        ],
        "field_settings": {
            "document_publication_year_start": {
                "index_field_name": "year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publication year start"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,                    
                }                
            },
            "document_publication_year_end": {
                "index_field_name": "year",
                "filter": {
                    "transform": {
                        "type": "year_range",
                        "sources": [
                            "document_publication_year_start",
                            "document_publication_year_end",
                        ]
                    },
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publication year end"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,                    
                }
            },
            "city_brazil": {
                "index_field_name": "cities.keyword",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("City"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "state_brazil": {
                "index_field_name": "states.keyword",
                "filter": {
                    "size": 27,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("State"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },
            },
            "action": {
                "index_field_name": "action.keyword",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Action"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },                
            },
            "classification": {
                "index_field_name": "classification.keyword",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Classification"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },                
            },
            "directory_type": {
                "index_field_name": "directory_type.keyword",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Directory Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },                
            },
            "institution": {
                "index_field_name": "institutions.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Institution"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                },                
            },
            "practice": {
                "index_field_name": "practice.keyword",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Pratice"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                },   
                
            },
            "thematic_level_0": {
                "index_field_name": "thematic_level_0.keyword",
                "filter": {
                    "size": 20,
                    "order": {
                        "_key": "asc"
                    },
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Thematic Level"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                },   
                
            },        
        }
    },    
    "journal_metrics": {
        "index_name": settings.ES_INDEX_JOURNAL_METRICS,
        "display_name": _("Journal Metrics"),
        "field_settings": {
            "country": {
                "index_field_name": "country.keyword",
                "filter": {
                    "size": 300,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "journal": {
                "index_field_name": "journal.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                    "support_search_as_you_type": True
                }
            },
            "openalex_region": {
                "index_field_name": "openalex_region.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "publisher_name": {
                "index_field_name": "publisher_name.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                    "support_search_as_you_type": True
                }
            },
            "scielo_collection_name": {
                "index_field_name": "scielo_collection_name.keyword",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "scielo_thematic_area": {
                "index_field_name": "scielo_thematic_areas.keyword",
                "filter": {
                    "size": 50,
                    "order": {
                        "_key": "asc"
                    },
                    "support_query_operator": True
                }
            },
            "scimago_region": {
                "index_field_name": "scimago_region.keyword",
                "filter": {
                    "size": 20,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "source_index": {
                "index_field_name": "source.keyword",
                "filter": {
                    "size": 50,
                    "order": {
                        "_key": "asc"
                    },
                    "support_query_operator": True
                }
            },
            "issn": {
                "index_field_name": "issns.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                    "support_search_as_you_type": True
                }
            },
            "year_founded": {
                "index_field_name": "year_of_creation_of_the_periodical",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "is_scielo": {
                "index_field_name": "is_scielo",
                "filter": {
                    "transform": {
                        "type": "boolean"
                    },
                    "size": 2,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "year": {
                "index_field_name": "year",
                "filter": {
                    "use": False,
                    "size": 200,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "cwts_snip": {
                "index_field_name": "cwts_snip",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "openalex_num_docs": {
                "index_field_name": "openalex_num_docs",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scielo_num_docs": {
                "index_field_name": "scielo_num_docs",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_best_quartile": {
                "index_field_name": "scimago_best_quartile",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "scimago_citable_docs_3_years": {
                "index_field_name": "scimago_citable_docs_3_years",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_cites_by_doc_2_years": {
                "index_field_name": "scimago_cites_by_doc_2_years",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_estimated_apc": {
                "index_field_name": "scimago_estimated_apc",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_estimated_value": {
                "index_field_name": "scimago_estimated_value",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_female_authors_percent": {
                "index_field_name": "scimago_female_authors_percent",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_overton": {
                "index_field_name": "scimago_overton",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_sdg": {
                "index_field_name": "scimago_sdg",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_sjr": {
                "index_field_name": "scimago_sjr",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_total_cites_3_years": {
                "index_field_name": "scimago_total_cites_3_years",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "scimago_total_docs_3_years": {
                "index_field_name": "scimago_total_docs_3_years",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            }
        }
    },
    "sources": {
        "index_name": settings.ES_INDEX_SOURCES,
        "display_name": _("Sources"),
        "field_settings": {
            "source_country": {
                "index_field_name": "country.keyword",
                "filter": {
                    "size": 300,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "source_name": {
                "index_field_name": "display_name.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "issn": {
                "index_field_name": "issn.keyword",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    },
                }
            }
        }
    }
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

def get_data_by_field_name(data_source, field_name):
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return field_settings[field_name]

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

def get_display_transform_by_field_name(data_source, field_name):
    """Get the display transform for a field."""
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return field_settings[field_name].get("settings", {}).get("display_transform")
    return None


def get_settings_by_field_name(data_source, field_name):
    """Get the display transform for a field."""
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return field_settings[field_name].get("settings", {})
    return None

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


def get_index_field_name_to_filter_name_map(data_source):
    field_settings = get_field_settings(data_source)
    if not field_settings:
        return {}

    return {
        setting.get("index_field_name"): key
        for key, setting in field_settings.items()
        if setting.get("index_field_name")
    }

def get_filters_to_exclude_by_data_source(data_source):
    return DATA_SOURCES.get(data_source, {}).get("filters_to_exclude")

def get_source_fields_by_data_source(data_source):
    return DATA_SOURCES.get(data_source, {}).get("source_fields")
