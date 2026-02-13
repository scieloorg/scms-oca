#!/usr/bin/env python3
"""
Mapping and index creation for bronze_dataverse.
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
            "publication_date": {
                "type": "date",
            },
            "publication_year": {
                "type": "long",
            },
            "type": {
                "type": "keyword",
                "fields": {
                    "keyword": {"type": "keyword"}
                },
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

