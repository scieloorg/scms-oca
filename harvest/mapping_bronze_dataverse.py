#!/usr/bin/env python3
"""
Mapping and index creation for bronze_scielo_dataverse.
"""


# --- Mapping for destination index ---
BRONZE_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
        },
        "analysis": {
            "analyzer": {
                "multilingual": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            },
        },
    },
    "mappings": {
        "dynamic": True,
        "properties": {
            "oca_data": {
                "type": "object",
                "properties": {
                    "scope": {"type": "keyword"},
                },
            },
            "title": {
                "type": "text",
                "analyzer": "multilingual",
                "copy_to": ["title_search"],
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 512,
                    }
                },
            },
            "title_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            }, 
            "ids": {
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "keyword",
                        "copy_to": ["ids_search"],
                    },
                },
            },
            "ids_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "content_url": {
                "type": "keyword",
                "index": False,
            },
            "is_released": {
                "type": "boolean",
            },
            "affiliation": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "description": {
                "type": "text",
                "analyzer": "multilingual",
            },
            "description_with_lang": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "text",
                        "analyzer": "multilingual",
                    },
                    "language": {"type": "keyword"},
                },
            },
            "publication_date": {
                "type": "date",
            },
            "publication_year": {
                "type": "long",
            },
            "sources": {
                "type": "object",
                "properties": {
                    "host_organization": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 256,
                                    }
                                },
                                "analyzer": "multilingual",
                                "type": "text",
                            },
                        },
                    },
                    "id": {"type": "keyword"},
                    "is_open_access": {"type": "boolean"},
                    "is_primary": {"type": "boolean"},
                    "issn_l": {"type": "keyword"},
                    "issns": {"type": "keyword"},
                    "landing_page_url": {"type": "keyword"},
                    "title": {
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            }
                        },
                        "copy_to": [
                            "sources_search",
                            "sources_search_autocomplete",
                        ],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                    "type": {"type": "keyword"},
                },
            },
            "sources_search": {
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
                "analyzer": "multilingual",
                "type": "text",
            },
            "sources_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type",
            },
            "dataverse_contacts": {
                "type": "object",
                "properties": {
                    "contact_email": {
                        "type": "keyword",
                    },
                    "display_order": {
                        "type": "integer",
                    },
                },
            },
            "subjects_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "subjects_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },                  
        },
    },
}

