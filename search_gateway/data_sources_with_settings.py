from django.conf import settings
from django.utils.translation import gettext_lazy as _


# Mapping from data source name to index and field settings
DATA_SOURCES = {
    "scientific": {
        "index_name": settings.OP_INDEX_ALL_BRONZE,
        "display_name": _("Scientific Production"),
        "filters_to_exclude": [
            "document_publication_year_start",
            "document_publication_year_end",
            "document_publication_year_range",
            "cited_by_count",
            "institution",
            "funder",
            "subjects",
            "source_name",
            "publisher",
        ],
        "field_settings": {
            # Scope
            "scope": {
                "index_field_name": "oca_data.scope",
                "filter": {"size": 5, "order": {"_key": "asc"}},
            },

            # Source level
            "source_indexed_in": {
                "index_field_name": "indexed_in",
                "filter": {"size": 10, "order": {"_key": "asc"}},
                "settings": {
                    "label": _("Indexed In"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "source",
                }
            },
            "publisher": {
                "index_field_name": "publishers_search.keyword",
                "field_autocomplete": "publishers_search_autocomplete",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publisher"),
                    "support_search_as_you_type": True,
                    "support_query_operator": True,
                    "category": "source",
                },
            },
            "source_name": {
                "index_field_name": "sources_search.keyword",
                "field_autocomplete": "sources_search_autocomplete",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source"),
                    "support_search_as_you_type": True,
                    "support_query_operator": True,
                    "category": "source",
                },
            },
            "source_type": {
                "index_field_name": "sources.type",
                "filter": {"size": 30, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "source",
                }
            },
            "source_country": {
                "index_field_name": "oca_data.source.country_search",
                "field_autocomplete": "oca_data.source.country_search_autocomplete",
                "filter": {"size": 10, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Country"),
                    "support_search_as_you_type": True,
                    "support_query_operator": True,
                    "category": "source",
                },
            },

            # Document level
            "publication_year": {
                "index_field_name": "publication_year",
                "filter": {"size": 300, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publication Year"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
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
            "document_type": {
                "index_field_name": "type",
                "filter": {"size": 30, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "document_language": {
                "index_field_name": "language",
                "filter": {"size": 500, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Language"),
                    "support_search_as_you_type": False,
                    "support_query_operator": True,
                    "category": "document",
                },
            },
            "open_access": {
                "index_field_name": "is_open_access",
                "filter": {
                    "transform": {"type": "boolean"},
                    "size": 2,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Open Access"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                }
            },
            "open_access_status": {
                "index_field_name": "open_access_status",
                "filter": {"size": 20, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Open Access Status"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "subject_area_level_0": {
                "index_field_name": "topic_domains",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Domain"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                }
            },
            "subject_area_level_1": {
                "index_field_name": "topic_fields",
                "filter": {"size": 27, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Field"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                }
            },
            "subject_area_level_2": {
                "index_field_name": "topic_subfields",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Subfield"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                }
            },
            "subjects": {
                "index_field_name": "subjects_search.keyword",
                "field_autocomplete": "subjects_search_autocomplete",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Subject"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "document",
                },
            },

            # Author affiliation level
            "institution": {
                "index_field_name": "institutions_search.keyword",
                "field_autocomplete": "institutions_search_autocomplete",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Institution"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "funder": {
                "index_field_name": "funders_search.keyword",
                "field_autocomplete": "funders_search_autocomplete",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Funder"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "country": {
                "index_field_name": "author_country_codes",
                "filter": {"size": 200, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Country"),
                    "support_search_as_you_type": False,
                    "support_query_operator": True,
                    "category": "author_affiliation",
                },
            },
            
            # Metrics fields
            "cited_by_count": {
                "index_field_name": "metrics.received_citations.total",
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
        },
    },
    "world": {
        "index_name": settings.OP_INDEX_SCI_PROD,
        "display_name": _("Scientific Production - Bronze"),
        "result_template": "search/include/result_items/world.html",
        "source_fields" : [
            "_id",
            "indexed_in",
            "primary_source_title",
            "primary_source_type",
            "primary_source_issns",
            "publication_year",
            "biblio.volume",
            "biblio.issue",
            "biblio.first_page",
            "title",
            "authorships",
            "language",
            "type",
            "is_open_access",
            "open_access_status",
            "oca_data.scope",
            "sources.landing_page_url",
            "metrics.received_citations.total",
        ],
        "filters_to_exclude": [
            "cited_by_count",
            "document_publication_year_start",
            "document_publication_year_end",
            "document_publication_year_range"            
        ],
        "field_settings": {
            # Scope field
            "scope": {
                "index_field_name": "oca_data.scope",
                "filter": {"size": 5, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Scope"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "source",
                },
            },
            
            # Source fields
            "source_indexed_in": {
                "index_field_name": "indexed_in",
                "filter": {"size": 30, "order": {"_key": "asc"}},
                "settings": {
                    "class_filter": "select2",
                    "label": _("Indexed in"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "source",
                },
            },
            "source_type": {
                "index_field_name": "primary_source_type",
                "filter": {
                    "size": 50,
                    "order": {"_key": "asc"},
                    "support_query_operator": False,
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "source",
                },
            },
            "source_name": {
                "index_field_name": "primary_source_title",
                "filter": {
                    "size": 1,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "source",
                },
            },
            "publisher": {
                "index_field_name": "publishers_search.keyword",
                "field_autocomplete": "publishers_search_autocomplete",
                "filter": {
                    "size": 1,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publisher"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "source",
                },
            },
            "funder": {
                "index_field_name": "funders_search.keyword",
                "field_autocomplete": "funders_search_autocomplete",
                "filter": {
                    "size": 1,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Funder"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "funding",
                },
            },
            "issn": {
                "index_field_name": "primary_source_issns",
                "filter": {
                    "size": 5,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("ISSN"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "source",
                },
            },

            # Document fields
            "access_type": {
                "index_field_name": "open_access_status",
                "filter": {
                    "size": 20,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Access Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "document_language": {
                "index_field_name": "language",
                "filter": {
                    "size": 500,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Language"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "display_transform": "language",
                    "category": "document",
                },
            },
            "document_type": {
                "index_field_name": "type",
                "filter": {
                    "size": 100,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "open_access": {
                "index_field_name": "is_open_access",
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
                    "category": "document",
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
                    "category": "document",
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
                "index_field_name": "topic_domains",
                "filter": {
                    "size": 3,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Domain"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "subject_area_level_1": {
                "index_field_name": "topic_fields",
                "filter": {
                    "size": 27,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Field"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "subject_area_level_2": {
                "index_field_name": "topic_subfields",
                "filter": {
                    "size": 500,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Subfield"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },

            # Author affiliation fields
            "institutions": {
                "index_field_name": "institutions_search.keyword",
                "field_autocomplete": "institutions_search_autocomplete",
                "filter": {
                    "size": 1,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Institution"),
                    "support_search_as_you_type": True,
                    "support_query_operator": True,
                    "category": "author_affiliation",
                },
            },
            "country": {
                "index_field_name": "author_country_codes",
                "filter": {
                    "size": 400,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Country"),
                    "support_search_as_you_type": False,
                    "support_query_operator": True,
                    "display_transform": "country",
                    "category": "author_affiliation",
                },
            },

            # Metrics fields
            "cited_by_count": {
                "index_field_name": "metrics.received_citations.total",
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
                "index_field_name": "oca_data.source.country_codes",
                "filter": {
                    "size": 400,
                    "order": {"_key": "asc"},
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Source Country"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "display_transform": "country",
                    "category": "source",
                },
            },
        },
    },
    "social_production": {
        "index_name": settings.OP_INDEX_SOC_PROD,
        "display_name": _("Social Production"),
        "result_template": "search/include/result_items/social_production.html",
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
                    "support_search_as_you_type": True,
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
        "index_name": settings.OPENSEARCH_INDEX_JOURNAL_METRICS,
        "display_name": _("Journal Metrics"),
        "field_settings": {
            "country": {
                "index_field_name": "country",
                "filter": {
                    "size": 500,
                    "order": {
                        "_key": "asc"
                    },
                }
            },
            "journal_title": {
                "index_field_name": "journal_title",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "journal_issn": {
                "index_field_name": "journal_issn",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "journal_id": {
                "index_field_name": "journal_id",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "publisher_name": {
                "index_field_name": "publisher_name",
                "filter": {
                    "size": 1,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "collection": {
                "index_field_name": "collection",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "category_level": {
                "index_field_name": "category_level",
                "filter": {
                    "size": 50,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "category_id": {
                "index_field_name": "category_id",
                "filter": {
                    "size": 1000,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "publication_year": {
                "index_field_name": "publication_year",
                "filter": {
                    "size": 200,
                    "order": {
                        "_key": "desc"
                    }
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
                    }
                }
            },
            "is_scopus": {
                "index_field_name": "is_scopus",
                "filter": {
                    "transform": {
                        "type": "boolean"
                    },
                    "size": 2,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "is_wos": {
                "index_field_name": "is_wos",
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
            "is_doaj": {
                "index_field_name": "is_doaj",
                "filter": {
                    "transform": {
                        "type": "boolean"
                    },
                    "size": 2,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "is_openalex": {
                "index_field_name": "is_openalex",
                "filter": {
                    "transform": {
                        "type": "boolean"
                    },
                    "size": 2,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "is_journal_multilingual": {
                "index_field_name": "is_journal_multilingual",
                "filter": {
                    "transform": {
                        "type": "boolean"
                    },
                    "size": 2,
                    "order": {
                        "_key": "asc"
                    }
                }
            },
            "journal_publications_count": {
                "index_field_name": "journal_publications_count",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_citations_total": {
                "index_field_name": "journal_citations_total",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_citations_mean": {
                "index_field_name": "journal_citations_mean",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_citations_mean_window_2y": {
                "index_field_name": "journal_citations_mean_window_2y",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_citations_mean_window_3y": {
                "index_field_name": "journal_citations_mean_window_3y",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_citations_mean_window_5y": {
                "index_field_name": "journal_citations_mean_window_5y",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_impact_normalized": {
                "index_field_name": "journal_impact_normalized",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_impact_normalized_window_2y": {
                "index_field_name": "journal_impact_normalized_window_2y",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_impact_normalized_window_3y": {
                "index_field_name": "journal_impact_normalized_window_3y",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "journal_impact_normalized_window_5y": {
                "index_field_name": "journal_impact_normalized_window_5y",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "top_1pct_all_time_publications_share_pct": {
                "index_field_name": "top_1pct_all_time_publications_share_pct",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "top_5pct_all_time_publications_share_pct": {
                "index_field_name": "top_5pct_all_time_publications_share_pct",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "top_10pct_all_time_publications_share_pct": {
                "index_field_name": "top_10pct_all_time_publications_share_pct",
                "filter": {
                    "use": False,
                    "size": 1,
                    "order": {
                        "_key": "desc"
                    },
                }
            },
            "top_50pct_all_time_publications_share_pct": {
                "index_field_name": "top_50pct_all_time_publications_share_pct",
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
    "bronze_all": {
        "index_name": "bronze_*",
        "display_name": _("Scientific Production"),
        "field_settings": {
            "document_type": {
                "index_field_name": "type.keyword",
                "filter":{
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                },
            },
            "publication_year": {
                "index_field_name": "publication_year",
                "filter": {
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publication Year"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                    
                }
            },
            "subjects": {
                "index_field_name": "subjects_search.keyword",
                "field_autocomplete": "subjects_search_autocomplete",
                "filter":{
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Subject"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "document",                    
                }
            },
            "publisher": {
                "index_field_name": "publisher_search.keyword",
                "field_autocomplete": "publisher_search_autocomplete",
                "filter":{
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publisher"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "document",                    
                }
            },
            "institutions": {
                "index_field_name": "institutions_search.keyword",
                "field_autocomplete": "institutions_search_autocomplete",
                "filter":{
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Institutions"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "document",                    
                }
            },
            "document_language": {
                "index_field_name": "language.keyword",
                "filter":{
                    "size": 100,
                    "order": {
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Document Language"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                    
                }
            }
        }
    },
    "bronze_social_production":{
        "index_name": settings.OP_INDEX_SOC_PROD,
        "display_name": _("Social Production"),
        "field_settings":{
            "publication_year": {
                "index_field_name": "year",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Publication year start"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }                
            },
            "action": {
                "index_field_name": "action",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Action"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "thematic_level_0": {
                "index_field_name": "thematic_level_0",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Thematic level 0"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",
                }
            },
            "thematic_level_1": {
                "index_field_name": "thematic_level_1",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Thematic level 1"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "thematic_level_3": {
                "index_field_name": "thematic_level_2",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Thematic level 2"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "practice": {
                "index_field_name": "practice",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Practice"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "institutions": {
                "index_field_name": "institutions_search.keyword",
                "field_autocomplete": "institutions_search_autocomplete",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Institutions"),
                    "support_search_as_you_type": True,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "classification": {
                "index_field_name": "classification",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Classification"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "cities": {
                "index_field_name": "cities",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Cities"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "states": {
                "index_field_name": "states",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("States"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            },
            "directory_type": {
                "index_field_name": "directory_type",
                "filter":{
                    "size": 20,
                    "order":{
                        "_key": "asc"
                    }
                },
                "settings": {
                    "class_filter": "select2",
                    "label": _("Directory Type"),
                    "support_search_as_you_type": False,
                    "support_query_operator": False,
                    "category": "document",                           
                }
            }
        }
    }
}

DATA_SOURCES["social"] = DATA_SOURCES["bronze_social_production"]


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

def get_field_autocomplete_from_data_source(data_source, field_name):
    field_settings = get_field_settings(data_source)
    if field_name in field_settings:
        return field_settings[field_name].get("field_autocomplete")
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

def get_result_template_by_data_source(data_source):
    """Get the result template path for a data source."""
    return DATA_SOURCES.get(data_source, {}).get("result_template", "")


def get_display_name_by_data_source(data_source):
    return DATA_SOURCES.get(data_source, {}).get("display_name", "")
