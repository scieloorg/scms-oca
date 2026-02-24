#!/usr/bin/env python3
"""
Mapping and index creation for bronze_preprint.
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
            "authors_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "authorships": {
                "type": "object",
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "copy_to": ["authors_search"],
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            }
                        },
                    },
                    "orcid": {"type": "keyword"},
                    "position": {"type": "keyword"},
                    "language": {"type": "keyword"}
                },
            },
            "abstract": {
                "type": "text",
                "analyzer": "multilingual",
            },
            "abstract_with_lang": {
                "type": "object",
                "properties": {
                    "abstract": {
                        "type": "text",
                        "analyzer": "multilingual",
                    },
                    "language": {"type": "keyword"},
                },
            },
            "ids": {
                "type": "object",
                "properties": {
                    "scl_preprint_id": {
                        "type": "keyword",
                        "copy_to": ["ids_search"],
                    },
                    "doi": {
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
            "language": {
                "copy_to": [
                    "language_search",
                    "language_search_autocomplete"
                ],
                "type": "keyword"
            },
            "language_search": {
                "fields": {
                    "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                    }
                },
                "analyzer": "multilingual",
                "type": "text"
            },
            "language_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type"
            },
            "language_normalized": {
                "type": "text",
                "fields": {
                    "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                    }
                }
            },            
            "oca_data": {
                "type": "object",
                "properties": {
                    "scope": {"type": "keyword"},
                },
            },
            "publication_date": {"type": "date"},
            "publication_year": {"type": "long"},
            "publishers": {
                "type": "object",
                "properties": {
                    "id": {
                    "type": "keyword"
                    },
                    "name": {
                    "fields": {
                        "keyword": {
                        "type": "keyword",
                        }
                    },
                    "copy_to": [
                        "publishers_search",
                        "publishers_search_autocomplete"
                    ],
                    "analyzer": "multilingual",
                    "type": "text"
                    }
                }
            },
            "publishers_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type",
            },
            "publishers_search": {
                "fields": {
                    "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                    }
                },
                "analyzer": "multilingual",
                "type": "text"
            },
            "rights": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "rights_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "rights": {
                        "type": "text",
                        "analyzer": "multilingual",
                    },
                },
            },
            "subjects": {
                "type": "text",
                "analyzer": "multilingual",
                "copy_to": ["subjects_search", "subjects_search_autocomplete"],
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "subjects_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "subjects": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            }
                        },
                    },
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
            "title_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "title": {
                        "fields":{
                            "keyword":{
                                "type": "keyword",
                            }
                        },
                        "copy_to": ["title_search"],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                },
            },
            "type": {
                "type": "keyword"
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
        },
    },
}

