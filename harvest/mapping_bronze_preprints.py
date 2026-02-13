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
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"}
                },
            },
            "oca_data": {
                "type": "object",
                "properties": {
                    "scope": {"type": "keyword"},
                },
            },
            "publication_date": {"type": "date"},
            "publication_year": {"type": "long"},
            "publisher": {
                "type": "text",
                "analyzer": "multilingual",
                "copy_to": ["publisher_search", "publisher_search_autocomplete"],
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "publisher_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "publisher_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "publisher_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "publisher": {
                        "type": "text",
                        "analyzer": "multilingual",
                    },
                },
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
                        "type": "text",
                        "analyzer": "multilingual",
                        "copy_to": ["title_search"],
                    },
                },
            },
            "type": {
                "type": "keyword",
                "fields": {
                    "keyword": {"type": "keyword"}
                },
            },
        },
    },
}

